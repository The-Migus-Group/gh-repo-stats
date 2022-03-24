import csv
import os
import json
from pathlib import Path
import click
import requests
import yaml
from rich.console import Console
from rich.table import Table


def get_repo_data(headers: dict, owner: str, repo: str) -> dict:
    """Fetches all data required for output for each repo"""
    #TODO: Handle missing data if non-200 response
    resp_data = requests.get(
        f"https://api.github.com/repos/{owner}/{repo}", headers=headers
    ).json()

    views = requests.get(
        f"https://api.github.com/repos/{owner}/{repo}/traffic/views", headers=headers
    ).json()

    clones = requests.get(
        f"https://api.github.com/repos/{owner}/{repo}/traffic/clones", headers=headers
    ).json()

    return {
        "Repo": f"{owner}/{repo}",
        "Forks": resp_data["forks_count"],
        "Stars": resp_data["stargazers_count"],
        "Watchers": resp_data["watchers_count"],
        "Clones Total": clones["count"],
        "Clones Unique": clones["uniques"],
        "Views Total": views["count"],
        "Views Unique": views["uniques"],
    }


def parse_repos_list_from_yaml(file) -> dict:
    """Parses the YAML file and converts to Python objects"""
    with open(file) as yaml_file:
        return yaml.safe_load(yaml_file)


@click.command()
@click.option("-r", "--repos", type=click.Path(exists=True), help="Yaml representation of Repos to Pull")
@click.option("-o", "--org", help="Pull stats for all repos owned by Org")
@click.option("-u", "--user", help="Pull stats for all repos owned by User")
@click.option("-f","--output-file", help="Output file path. Only supports CSV or JSON")
@click.option("-t", "--auth-token", help="GitHb Access Token")
def main(repos, org, user, output_file, auth_token):
    """Fetch GitHub repo stats!"""

    #TODO: Take token as envvar or as cli option and handle missing token
    if auth_token:
        HEADERS = {"Authorization": f"token {auth_token}"}
    else:
        try:
            HEADERS = {"Authorization": f"token {os.getenv('GH_TOKEN')}"}
        except:
            ValueError("Please set a GitHub Access Token.")

    # Pull repos list from either source
    if repos:
        repos_dict = parse_repos_list_from_yaml(repos)
    elif org:
        owner = org.strip().strip('/')
        org_repos = requests.get(f"https://api.github.com/orgs/{owner}/repos", headers=HEADERS).json()
        repo_names = [repo["name"] for repo in org_repos]
        repos_dict = {"Owners": [{owner: repo_names}]}
    elif user:
        owner = user.strip().strip('/')
        org_repos = requests.get(f"https://api.github.com/users/{owner}/repos", headers=HEADERS).json()
        repo_names = [repo["name"] for repo in org_repos]
        repos_dict = {"Owners": [{owner: repo_names}]}


    # Iterate list and pull data
    # Pass dict to get repo data - finish with list of dicts
    final_data = []
    for repo_owner in repos_dict["Owners"]:
        key = next(iter(repo_owner))
        for repo in repo_owner[key]:
            final_data.append(get_repo_data(HEADERS, key, repo))

    # Pass data to output type
    # Pass list of dicts to output fuction
    if output_file:
        file_path = Path(output_file)

        if file_path.suffix == '.csv':
            print("Creating CSV")
            with open("data.csv", "w", newline='') as file:
                writer = csv.DictWriter(
                    file,
                    fieldnames=[
                        "Repo",
                        "Forks",
                        "Stars",
                        "Watchers",
                        "Clones Total",
                        "Clones Unique",
                        "Views Total",
                        "Views Unique",
                    ],
                )
                writer.writeheader()

                for data in final_data:
                    writer.writerow(
                        {
                            "Repo": data["Repo"],
                            "Forks": data["Forks"],
                            "Stars": data["Stars"],
                            "Watchers": data["Watchers"],
                            "Clones Total": data["Clones Total"],
                            "Clones Unique": data["Clones Unique"],
                            "Views Total": data["Views Total"],
                            "Views Unique": data["Views Unique"],
                        }
                    )

            print("CSV file created.")

        elif file_path.suffix == '.json':
            print("Creating JSON")
            with open(file_path, "w") as file:
                file_data = {"Data": [data for data in final_data]}
                file.write(json.dumps(file_data, indent=4))

        else:
            raise ValueError("Output file must be CSV or JSON")

    else:
        table = Table(title="GitHub Stats")
        table.add_column("Repo")
        table.add_column("Forks", justify="center")
        table.add_column("Stars", justify="center")
        table.add_column("Watchers", justify="center")
        table.add_column("Clones Total", justify="center")
        table.add_column("Clones Unique", justify="center")
        table.add_column("Views Total", justify="center")
        table.add_column("Views Unique", justify="center")

        for data in final_data:
            table.add_row(
                str(data["Repo"]),
                str(data["Forks"]),
                str(data["Stars"]),
                str(data["Watchers"]),
                str(data["Clones Total"]),
                str(data["Clones Unique"]),
                str(data["Views Total"]),
                str(data["Views Unique"]),
            )

        console = Console()
        console.print(table)


if __name__ == "__main__":
    main()