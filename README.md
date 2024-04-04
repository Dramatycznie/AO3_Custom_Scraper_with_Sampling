# AO3 Custom Scraper with Sampling
A Python tool designed for in-depth scraping of Archive of Our Own (AO3) content, tailored through `config.ini` configurations. It specializes in extracting data based on specific AO3 tags or searches, offering high customization.

## Table of Contents
- [Features](#features)
- [Dependencies](#dependencies)
- [Configuration](#configuration)
- [How to Use](#how-to-use)
- [Contact](#contact)
- [Bug Reports and Feature Requests](#bug-reports-and-feature-requests)

## Features
- **Customizable Scraping**: Tailored data extraction from AO3, configurable via `config.ini` for specific tags or search queries.
- **Recovery**: Features the ability to resume scraping tasks after interruptions, minimizing data loss and ensuring completeness of data collection.
- **Custom User Agents**: Utilizes custom user agents to simulate different browsers.
- **Structured Data Output**: Organizes extracted data into CSV format, supporting both analysis and archival purposes.
- **Configurable Delays and Pagination**: Manages scraping intensity with adjustable delays and page range settings to responsibly interact with AO3's servers.
- **Sampling Strategies**: Offers multiple sampling methods (random, strata, systematic) for targeted data collection.
- **Output Customization**: Flexible CSV output settings including file naming, path specifications, and append/overwrite modes.

## Dependencies
- Python 3
- requests
- BeautifulSoup
- tqdm
- configparser

Install dependencies with `pip install -r requirements.txt`.

## Configuration
Customize your scraping with `config.ini`. Here are the settings grouped by theme:

### Request Settings
- **user_agent**: Mimic browser requests, if needed.
  - `Example: user_agent = Mozilla/5.0 ...`
- **url**: Base URL for AO3 with your applied filters.
  - `Example: url = https://archiveofourown.org/tags/YourFandom/works`
- **delay**: Time in seconds between requests, to prevent server overload.
  - `Example: delay = 5`

### Scraping Scope
- **start_page**: Page number to start scraping from.
  - `Example: start_page = 1`
- **end_page**: Page number to stop scraping at. Leave blank for no limit.
  - `Example: end_page = 10`
- **max_work_count**: Maximum works to scrape. Overrides end page settings.
  - `Example: max_work_count = 100`

### Output Settings
- **csv_file**: Name of the file where scraped data will be saved.
  - `Example: csv_file = my_scraped_data`
- **csv_path**: Where to save the CSV file.
  - `Example: csv_path = /path/to/directory/`
- **file_mode**: Whether to append (`a`) or overwrite (`w`) the CSV file.
  - `Example: file_mode = a`
- **internal_delimiter**: Delimiter used in the CSV file.
  - `Example: internal_delimiter = ;`

### Sampling Settings
- **sampling_strategy**: Choose from `null`, `random`, `systematic`, `strata`.
  - `Example: sampling_strategy = random`
- **sampling_percentage**: For `random` strategy, percentage of works to sample.
  - `Example: sampling_percentage = 25`
- **sampling_n**: For `systematic` strategy, interval of works to sample.
  - `Example: sampling_n = 2`
- **kudos_bins**: For `strata` strategy, bins of kudos to define strata.
  - `Example: kudos_bins = 0, 100, 200, 500`

Configure these options to fine-tune how the scraper operates, ensuring output tailored to your specific needs.


## How to Use
1. Ensure you have Python 3 and all dependencies installed.
2. Configure `config.ini` according to your scraping needs.
3. Run `python main.py` to start scraping.
4. In case of interruption, the scraper can resume from where it left off, based on stored progress.

# Contact
If you have any questions or feedback about this project, please feel free to reach out to me.
- Email: mellodramat@gmail.com
- GitHub: https://github.com/Dramatycznie

# Bug reports and feature requests
For bug reports and feature requests, please open an issue on my GitHub repository: https://github.com/Dramatycznie/AO3_Custom_Scraper_with_Sampling/issues
