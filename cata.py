import requests
import json
import sys

def fetch_catalog_descriptors(token):
    base_url = 'https://api.getcortexapp.com/api/v1/catalog/descriptors'
    headers = {"Authorization": f"Bearer {token}"}
    all_descriptors = []  # To store descriptors from all pages
    page = 0
    totalPages = 1  # Initial assumption; will update based on API response

    while page <= totalPages:
        params = {"page": page}
        response = requests.get(base_url, headers=headers, params=params)
        response.raise_for_status()  # Ensure the request succeeded
        data = response.json()

        # Update totalPages based on the API response
        totalPages = data.get("totalPages", totalPages)

        # Append the current page's descriptors to the all_descriptors list
        if 'descriptors' in data:
            all_descriptors.extend(data['descriptors'])

        print(f"Fetched page: {page}/{totalPages}. Total descriptors fetched so far: {len(all_descriptors)}")

        # Prepare for the next page
        page += 1

    return all_descriptors




def extract_descriptor_details(descriptor):
    info = descriptor.get('info', {})
    git_info = info.get('x-cortex-git', {}).get('github', {}).get('repository', 'Missing')

    # Check for valid collectorsgroup repo pattern
    collectors_group_valid = git_info.startswith("collectorsgroup/") if git_info != 'Missing' else False

    # The check for interested_repos is removed, and git_info is directly used to determine validity
    x_cortex_git = f"GitHub: {git_info}" if git_info != 'Missing' and collectors_group_valid else "Invalid or Missing Repository"
    # Extract x-cortex-type information
    x_cortex_type = info.get('x-cortex-type', 'Missing')
    
    # Ensure x-cortex-type is provided
    valid_x_cortex_type = x_cortex_type != 'Missing'
 
    
    slack_info = descriptor.get('info', {}).get('x-cortex-slack', {})

    # Check if 'slack_info' is in the unexpected list format
    if isinstance(slack_info, list) and len(slack_info) > 0 and 'channels' in slack_info[0]:
        # Assume 'channels' are properly defined in the first dictionary of the list
        slack_channels_info = slack_info[0].get('channels', [])
    elif isinstance(slack_info, dict):
        # This is the directly accepted structure where 'slack_info' is a dictionary
        slack_channels_info = slack_info.get('channels', [])
    else:
        slack_channels_info = []

    # Construct 'x-cortex-slack-channels' from the 'slack_channels_info'
    if slack_channels_info:
        x_cortex_slack_channels = ', '.join([
            f"{channel.get('name', 'Unknown')}: {channel.get('description', 'No description provided')}"
            for channel in slack_channels_info
        ])
    else:
        x_cortex_slack_channels = 'Missing'
        
    

    print(slack_info) 
    

    oncall_info = info.get('x-cortex-oncall', {})
    if isinstance(oncall_info, dict):
        x_cortex_oncall_info = oncall_info.get('pagerduty', {}).get('id', 'Missing')
    else:
        x_cortex_oncall_info = 'Missing'

    issues_info = info.get('x-cortex-issues', {})
    if isinstance(issues_info, dict) and 'jira' in issues_info and isinstance(issues_info['jira'], dict):
        jira_projects = issues_info['jira'].get('projects', [])
        x_cortex_issues = ', '.join(jira_projects) if jira_projects else 'Missing'
    else:
        x_cortex_issues = 'Missing'

    parents_info = info.get('x-cortex-parents', [])
    x_cortex_parents = ', '.join([parent.get('tag', 'Missing') for parent in parents_info]) if parents_info else 'Missing'
    print(parents_info)
    details = {
        'title': info.get('title', 'No Title'),
        'x-cortex-tag': info.get('x-cortex-tag', 'Missing'),
        'x-cortex-git': x_cortex_git,
        'x-cortex-owners': ', '.join([owner.get('name', 'Missing') for owner in info.get('x-cortex-owners', []) if owner.get('provider') == "CORTEX" and owner.get('type') != 'slack']) or 'Missing',
        'x-cortex-slack-channels': x_cortex_slack_channels if slack_channels_info else 'Missing',
        'x-cortex-oncall': x_cortex_oncall_info if oncall_info else 'Missing',
        'x-cortex-issues': x_cortex_issues,
        'x-cortex-parents': x_cortex_parents,
        'x-cortex-type': x_cortex_type if valid_x_cortex_type else 'Missing Type'
    }

    #has_missing = any(value == 'Missing' for value in details.values())
    has_missing = any(value in ['Missing', 'Invalid or Missing Repository', 'Missing Type'] for value in details.values())
    return details, has_missing





def categorize_and_write_descriptors(descriptors):
    no_missing_items = []
    with_missing_items = []

    for descriptor in descriptors:
        details, has_missing = extract_descriptor_details(descriptor)
        if has_missing:
            with_missing_items.append(details)
        else:
            no_missing_items.append(details)

    # Write to files
    with open('no_missing_items.json', 'w') as f:
        json.dump(no_missing_items, f, indent=4)
    with open('with_missing_items.json', 'w') as f:
        json.dump(with_missing_items, f, indent=4)

    print(f"Descriptors with no missing items written to no_missing_items.json")
    print(f"Descriptors with missing items written to with_missing_items.json")




def main(token):
    descriptors = fetch_catalog_descriptors(token)
    if descriptors:
        print("Processing descriptors...")
        categorize_and_write_descriptors(descriptors)
        print("Finished processing descriptors.")
    else:
        print("Failed to fetch catalog descriptors or no descriptors found.")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python script.py <token>")
        sys.exit(1)
    token = sys.argv[1]
    main(token)
