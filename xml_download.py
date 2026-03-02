"""Download XML and PDF papers from Elsevier and Sci-Hub."""

import os
from typing import Any

import requests
from dotenv import load_dotenv
from scidownl import scihub_download


def save_xml(doi: str, xml_content: str, output_dir: str = "paper") -> None:
    """Save XML content to a file named after the DOI."""
    os.makedirs(output_dir, exist_ok=True)
    filename = os.path.join(output_dir, doi.replace("/", "_") + ".xml")
    with open(filename, "w", encoding="utf-8") as f:
        f.write(xml_content)
    print(f"XML saved to {filename}")


def download_pdf(doi: str, output_dir: str = "paper", proxies: dict[str, str] | None = None) -> None:
    """Download a PDF from Sci-Hub using the DOI."""
    os.makedirs(output_dir, exist_ok=True)
    paper_url = f"https://doi.org/{doi}"
    out = os.path.join(output_dir, doi.replace("/", "_") + ".pdf")
    scihub_download(paper_url, paper_type="doi", out=out, proxies=proxies)
    print(f"PDF attempted download to {out}")


def main() -> None:
    """Main entry point for downloading papers."""
    load_dotenv()
    api_key = os.getenv("scopus_api_key_tian") # Replace with your API key here
    if not api_key:
        print("API key not found in environment variables.")
        return

    dois = [ # two examples from Elsevier and MDPI; replace them by the doi's list from the abstract spreadsheet
        # "10.1016/j.pce.2025.103951",
        "10.3390/w12123305"
    ]

    headers = {
        "X-ELS-APIKey": api_key,
        "Accept": "text/xml"
    }

    proxies = {
        "http": "socks5://127.0.0.1:7890"
    }

    for doi in dois:
        url = f"https://api.elsevier.com/content/article/doi/{doi}"
        try:
            response = requests.get(url, headers=headers, timeout=15)
            if response.status_code == 200:
                save_xml(doi, response.text)
            else:
                print(f"Failed to fetch XML for {doi} (status {response.status_code}), trying Sci-Hub PDF...")
                download_pdf(doi, proxies=proxies)
        except Exception as e:
            print(f"Error processing {doi}: {e}")

if __name__ == "__main__":
    main()