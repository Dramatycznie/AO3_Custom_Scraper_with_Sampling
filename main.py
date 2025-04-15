import configparser
import csv
import os
import random
import requests
import socket
import time
import json
from urllib.parse import urlparse, urlunparse, parse_qs, urlencode
from bs4 import BeautifulSoup
from tqdm import tqdm

# Global variables
strata_counts = {}
seen_work_ids = set()


# Loads the config file
def load_config():
    config = configparser.ConfigParser(interpolation=None)

    if not os.path.exists('config.ini'):
        print("Error: config.ini file not found.")
        return None

    try:
        config.read('config.ini')
        return config['Settings']

    except Exception as e:
        print(f"Error: Could not read the INI file. {e}")
        return None


# Function to update the 'page' query parameter in a URL
def update_url_page_number(url, page_number):
    parsed_url = urlparse(url)
    query_params = parse_qs(parsed_url.query)
    query_params['page'] = [str(page_number)]
    new_query_string = urlencode(query_params, doseq=True)
    return urlunparse((parsed_url.scheme, parsed_url.netloc, parsed_url.path, parsed_url.params, new_query_string,
                       parsed_url.fragment))


# Gets the text of an element
def get_element_text(element):
    return element.text.strip() if element else ""


# Gets the text of a list of elements
def get_element_text_list(elements):
    return [element.text.strip() for element in elements] if elements else []


def scrape_single_work(work, csvwriter, internal_delimiter, delay, user_agent, page, kudos_bins):
    # First, check if there's a title
    title_element = work.select_one("h4 a")
    if title_element:
        title = get_element_text(title_element)
    else:
        return

    # Get ID of the work, and check if it's already been scraped
    work_id = work.get('id').split('_')[-1] if work.get('id') else None
    if work_id in seen_work_ids:
        return

    # Get the rest of the fields
    authors = get_element_text_list(work.select("a[rel='author']"))
    fandoms = get_element_text_list(work.select(".fandoms a"))
    warnings = get_element_text_list(work.select("li.warnings a.tag"))
    ratings = get_element_text_list(work.select("span.rating"))
    categories = get_element_text_list(work.select("span.category"))
    tags = get_element_text_list(work.select("li.freeforms a.tag"))
    characters = get_element_text_list(work.select("li.characters a.tag"))
    relationships = get_element_text_list(work.select("li.relationships a.tag"))
    date_updated = get_element_text(work.select_one("p.datetime"))
    words = get_element_text(work.select_one("dd.words"))

    # Handle the chapters string
    chapters_element = work.select_one("dd.chapters")
    if chapters_element:

        a_tag = chapters_element.select_one("a")
        if a_tag:
            chapters = a_tag.text.strip() + chapters_element.contents[-1].strip()
        else:
            chapters = chapters_element.text.strip()
    else:
        chapters = ""

    # Get the rest of the fields
    comments = get_element_text(work.select_one("dd.comments a")) or "0"
    kudos = get_element_text(work.select_one("dd.kudos a")) or "0"
    bookmarks = get_element_text(work.select_one("dd.bookmarks a")) or "0"
    hits = get_element_text(work.select_one("dd.hits")) or "0"
    language = get_element_text(work.select_one("dd.language"))
    collections = get_element_text(work.select_one("dd.collections a")) or "0"
    work_url = "https://archiveofourown.org" + work.select_one("h4 a")["href"]
    status_element = work.select_one(".complete-no, .complete-yes")

    # Get the status of the work
    if status_element:
        if "complete-no" in status_element.get("class"):
            status = "Incomplete"
        elif "complete-yes" in status_element.get("class"):
            status = "Complete"
        else:
            status = "Unknown"
    else:
        status = "Unknown"

    # Get the publication date of the work (has to be taken from the work page)
    try:
        headers = {'User-Agent': user_agent}
        response = requests.get(work_url, headers=headers)
        time.sleep(delay)

        if not handle_rate_limit(response, page):
            return  # Skip this work

        work_soup = BeautifulSoup(response.text, 'html.parser')
        date_published = get_element_text(work_soup.select_one("dd.published"))

    except Exception as e:
        print(f"Error fetching details for {work_url}: {e}")
        date_published = "Unknown"

    # Replace dashes with dots in dates for consistency
    if date_published:
        date_published = date_published.replace("-", ".")

    # Replace commas with delimiters in categories
    categories = [category.replace(', ', f'{internal_delimiter}') for category in categories]

    # Remove commas from these fields
    comments = comments.replace(",", "")
    kudos = int(kudos.replace(",", ""))
    bookmarks = bookmarks.replace(",", "")
    hits = hits.replace(",", "")
    words = words.replace(",", "")

    # Write row to CSV file
    csvwriter.writerow([
        work_id, work_url, title, f'{internal_delimiter}'.join(authors) if authors else 'Anonymous',
        f'{internal_delimiter}'.join(fandoms), language, f'{internal_delimiter}'.join(warnings),
        f'{internal_delimiter}'.join(ratings), f'{internal_delimiter}'.join(categories),
        f'{internal_delimiter}'.join(characters), f'{internal_delimiter}'.join(relationships),
        f'{internal_delimiter}'.join(tags), words, date_published, date_updated, chapters, comments, kudos, bookmarks,
        hits, collections, status
    ])

    # Add the work_id to seen_work_ids
    seen_work_ids.add(work_id)

    # Write seen_work_ids to a file
    with open('seen_work_ids.txt', 'a') as f:
        f.write(work_id + '\n')

    # Find the appropriate bin
    for bin_start, bin_end in zip(kudos_bins[:-1], kudos_bins[1:]):
        if bin_start <= kudos < bin_end:
            strata_counts[bin_start] += 1
            break

    # Save strata_counts to a file
    with open('strata_counts.json', 'w') as f:
        json.dump(strata_counts, f)


# Scrape the bookmarks of a user
def scrape_works(start_page, end_page, last_visited_page, delay, url, full_csv_path, internal_delimiter, max_work_count,
                 sampling_strategy, sampling_percentage, sampling_n, kudos_bins, file_mode, user_agent):
    global strata_counts
    strata_counts = {k: 0 for k in kudos_bins[:-1]}

    # Load seen_work_ids from a file if it exists
    if os.path.exists('seen_work_ids.txt'):
        with open('seen_work_ids.txt', 'r') as f:
            seen_work_ids.update(f.read().strip().split('\n'))

    write_header = True
    if file_mode == 'a' and os.path.exists(full_csv_path):
        write_header = False

    with open(full_csv_path, file_mode, newline='', encoding='utf-8') as csvfile:
        csvwriter = csv.writer(csvfile)

        if write_header:
            # Write header row to CSV file
            csvwriter.writerow(
                ['Work ID', 'URL', 'Title', 'Authors', 'Fandoms', 'Language', 'Warnings', 'Ratings', 'Categories',
                 'Characters', 'Relationships', 'Tags', 'Words', 'Date Published', 'Date Updated', 'Chapters',
                 'Comments', 'Kudos', 'Bookmarks', 'Hits', 'Collections', 'Completion Status'])

        work_count = 0

        if last_visited_page:
            start_page = last_visited_page

        page = start_page

        should_break = False

        while True:
            if end_page and page > end_page:
                break

            updated_url = update_url_page_number(url, page)

            max_retries = 3
            retry_count = 0

            while retry_count < max_retries:
                try:
                    headers = {'User-Agent': user_agent}
                    response = requests.get(updated_url, headers=headers)
                    time.sleep(delay)

                    if not handle_rate_limit(response, page):  # catch 4xx/5xx here
                        raise requests.exceptions.HTTPError(f"Bad status: {response.status_code}")

                    soup = BeautifulSoup(response.text, 'html.parser')
                    break  # success

                except (requests.exceptions.ConnectionError, requests.exceptions.ReadTimeout,
                        requests.exceptions.ConnectTimeout, socket.timeout,
                        requests.exceptions.HTTPError) as e:
                    print(f"Error scraping page {page}: {e}. Retrying...")
                    retry_count += 1

                    if retry_count >= max_retries:
                        print("Exceeded maximum retries. Please check your connection and try again later.")
                        input("Press Enter to exit...")
                        exit(0)

            works_on_page = soup.select("li.work")

            # Apply sampling here
            sampled_works = apply_sampling(sampling_strategy, sampling_percentage, works_on_page, sampling_n,
                                           kudos_bins)

            with tqdm(total=len(sampled_works), desc=f"Scraping page {page}: ") as pbar:
                with open("last_visited_page.txt", "w") as f:
                    f.write(str(page))
                for work in sampled_works:
                    work_id = work.get('id').split('_')[-1] if work.get('id') else None
                    if work_id in seen_work_ids:
                        continue

                    # Scrape the single work here
                    scrape_single_work(work, csvwriter, internal_delimiter, delay, user_agent, page, kudos_bins)
                    work_count += 1  # Increase the work_count (for max_work_count)
                    pbar.update(1)

                    # Check if max_work_count is reached
                    if max_work_count and work_count >= max_work_count:
                        should_break = True
                        break

            # Check if we need to break the while loop
            if should_break:
                break

            page += 1  # Move to the next page


def apply_sampling(sampling_strategy, sampling_percentage, works_on_page, sampling_n, kudos_bins):
    global strata_counts

    if sampling_strategy == "strata":
        # Reinitialize strata counts for this application of sampling to reflect current page distribution
        # (To keep a running total, move this initialization outside of this function)
        current_page_strata_counts = {bin_start: 0 for bin_start in kudos_bins[:-1]}

        # Initialize a dictionary to categorize works by kudos bins
        works_by_kudos = {}
        for bin_start, bin_end in zip(kudos_bins[:-1], kudos_bins[1:]):
            works_by_kudos[(bin_start, bin_end)] = []

        # Categorize each work into the appropriate kudos bin
        for work in works_on_page:
            kudos_text = get_element_text(work.select_one("dd.kudos a")) or "0"
            kudos = int(kudos_text.replace(',', ''))
            for bin_start, bin_end in zip(kudos_bins[:-1], kudos_bins[1:]):
                if bin_start <= kudos < bin_end:
                    works_by_kudos[(bin_start, bin_end)].append(work)
                    # Update the count for the current page as works are categorized
                    current_page_strata_counts[bin_start] += 1
                    break

        # Find the minimum count among the bins that have at least one work
        counts = [count for count in current_page_strata_counts.values() if count > 0]
        min_count = min(counts) if counts else 0  # Default to 0 if no works are found

        sampled_works = []

        # Sample an equal number of works from each bin based on the minimum count
        for (bin_start, bin_end), work_bin in works_by_kudos.items():
            if len(work_bin) > 0 and min_count > 0:  # Check to ensure bin is not empty and min_count is not 0
                sampled_works += random.sample(work_bin, min_count)
                # Update the global strata counts for sampled works
                strata_counts[bin_start] = strata_counts.get(bin_start, 0) + min_count

    elif sampling_strategy == "random":
        # Sample a percentage of works randomly from the page
        sample_size = int(len(works_on_page) * (sampling_percentage / 100))
        sampled_works = random.sample(works_on_page, min(len(works_on_page), sample_size))

    elif sampling_strategy == "systematic":
        # Systematically sample works starting from a random point
        start = random.randint(0, sampling_n - 1)
        sampled_works = works_on_page[start::sampling_n]

    else:
        # If no sampling strategy is specified, include all works
        sampled_works = works_on_page

    return sampled_works


# Handle the situation when the rate limit is exceeded
def handle_rate_limit(response, page):
    try:
        response.raise_for_status()
    except requests.exceptions.HTTPError as e:
        print(f"There had been an issue. Skipping. You might need to try again later. {e}")
        return False  # Don't exit, just return failure

    soup = BeautifulSoup(response.text, 'html.parser')
    if "Retry later" in soup.text:
        print(f"Rate limit exceeded while fetching details. Stopping and saving last visited page: {page}. "
              f"Please try again later. Your progress has been saved.")
        input("Press Enter to exit...")
        exit(0)

    return True


def main():
    try:
        global strata_counts
        print("Initializing...")
        # Load config
        config = load_config()
        if config is None:
            return

        try:
            url = config.get('url')
            if url is None:
                raise KeyError('url')

            try:
                with open("last_visited_page.txt", "r") as f:
                    last_visited_page = int(f.read().strip())
            except FileNotFoundError:
                last_visited_page = None

            start_page = int(config.get('start_page') or 1)
            end_page = config.get('end_page' or None)

            if end_page:
                end_page = int(end_page)

            file_mode = config.get('file_mode') or 'w'
            delay = int(config.get('delay') or 5)
            csv_file = config.get('csv_file') or 'scraped_works'
            internal_delimiter = config.get('internal_delimiter') or '; '
            max_work_count = config.get('max_work_count')

            if max_work_count:
                max_work_count = int(max_work_count)

            csv_path = config.get('csv_path') or './'
            full_csv_path = f"{csv_path}{csv_file}.csv"
            user_agent = config.get('user_agent') or "AO3 Sample Scraper Bot"

            # Sampling (default: no sampling. Options: random, systematic, strata)
            sampling_strategy = config.get("sampling_strategy", None)
            sampling_percentage = int(config.get("sampling_percentage") or 50)
            sampling_n = int(config.get("sampling_n") or 2)
            kudos_bins = [int(x.strip()) for x in config.get("kudos_bins", "0, 100, 500, 1000, 5000").split(",")]

            if kudos_bins:
                kudos_bins = [int(x) for x in kudos_bins]

        except KeyError as e:
            print(f"Error: {e} not specified in config file.")
            return

        except ValueError as e:
            print(f"Error: Could not convert a setting to its required type. {e}")
            return

        # If max_work_count is specified, set pages to default values (as we will be scraping the amount of works
        # specified)
        if max_work_count:
            start_page = 1
            end_page = None

        # Load strata_counts from a file if it exists
        if os.path.exists('strata_counts.json'):
            with open('strata_counts.json', 'r') as f:
                strata_counts = json.load(f)
        else:
            strata_counts = {k: 0 for k in kudos_bins[:-1]}

        # Scrape the works
        scrape_works(start_page, end_page, last_visited_page, delay, url, full_csv_path, internal_delimiter,
                     max_work_count, sampling_strategy, sampling_percentage, sampling_n, kudos_bins, file_mode,
                     user_agent)

        # If everything went well, delete the last_visited_page.txt, seen_work_ids.txt and strata_counts.json files
        if os.path.exists("last_visited_page.txt"):
            os.remove("last_visited_page.txt")
        if os.path.exists("seen_work_ids.txt"):
            os.remove("seen_work_ids.txt")
        if os.path.exists("strata_counts.json"):
            os.remove("strata_counts.json")

        # Message at the end, if everything went well
        print(f"Done.")

    except KeyboardInterrupt:
        print("Keyboard interrupt detected. Exiting...")
        exit(0)


if __name__ == '__main__':
    main()
