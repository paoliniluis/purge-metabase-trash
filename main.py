import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

import requests
import os
import logging
from typing import List, Dict

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Environment variables or defaults
METABASE_HOST = os.environ.get('host', 'https://localhost:8443')
USER = os.environ.get('user', 'a@b.com')
PASSWORD = os.environ.get('password', 'metabot1')

# --- Session Setup ---
session = requests.Session()
session.verify = False # Consider using proper certificate verification in production

def login() -> bool:
    """Logs into Metabase and sets up the session."""
    login_url = f"{METABASE_HOST}/api/session"
    login_payload = {"username": USER, "password": PASSWORD}
    try:
        response = session.post(login_url, json=login_payload)
        response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)
        logging.info("Successfully logged into Metabase.")
        return True
    except requests.exceptions.RequestException as e:
        logging.error(f"Login failed: {e}")
        return False

# --- Recursive Item Fetching ---
def get_all_items_recursive(collection_id: int) -> List[Dict[str, any]]:
    """
    Recursively fetches all non-collection items within a given collection
    and all its sub-collections.
    """
    items_to_process = []
    collection_endpoint = f"{METABASE_HOST}/api/collection/{collection_id}/items"
    params = {
        "models": ["dashboard", "dataset", "card", "metric", "snippet", "collection"],
        "show_dashboard_questions": "true"
    }
    try:
        response = session.get(collection_endpoint, params=params)
        response.raise_for_status()
        collection_data = response.json().get("data", [])

        for item in collection_data:
            item_model = item.get("model")
            item_id = item.get("id")

            if not item_model or item_id is None:
                logging.warning(f"Skipping item with missing model or id in collection {collection_id}: {item}")
                continue

            if item_model == "collection":
                # Recursively get items from the sub-collection
                logging.debug(f"Entering sub-collection {item_id}...")
                sub_collection_items = get_all_items_recursive(item_id)
                items_to_process.extend(sub_collection_items)
                # Also add the collection itself to be processed (deleted) later
                items_to_process.append({"model": item_model, "id": item_id})
            else:
                # Add non-collection items directly
                items_to_process.append({"model": item_model, "id": item_id})

    except requests.exceptions.RequestException as e:
        logging.error(f"Failed to get items from collection {collection_id}: {e}")
    except Exception as e:
        logging.error(f"An unexpected error occurred while processing collection {collection_id}: {e}")

    return items_to_process

# --- Deletion Logic ---
def delete_items(items: List[Dict[str, any]]):
    """Deletes a list of Metabase items."""
    # Right now we can't hard delete collections, so these will stay, but the script is prepared for that for the future
    deleted_count = 0
    failed_count = 0
    for item in items:
        model = item['model']
        item_id = item['id']
        delete_endpoint = f"{METABASE_HOST}/api/{model}/{item_id}"
        try:
            response = session.delete(delete_endpoint)
            if response.status_code == 204: # No Content is typical for successful DELETE
                logging.info(f"Successfully deleted {model} with id {item_id}")
                deleted_count += 1
            # Handle potential different success codes if needed
            elif 200 <= response.status_code < 300:
                 logging.info(f"Deleted {model} with id {item_id} (Status: {response.status_code})")
                 deleted_count += 1
            else:
                 # Raise for non-2xx status codes not handled above
                 response.raise_for_status()
        except requests.exceptions.RequestException as e:
            logging.error(f"Failed to delete {model} with id {item_id}: {e}, or {model} has already been deleted in cascade.")
            failed_count += 1
        except Exception as e:
            logging.error(f"An unexpected error occurred deleting {model} {item_id}: {e}")
            failed_count += 1

    logging.info(f"Deletion summary: {deleted_count} succeeded, {failed_count} failed.")


# --- Main Execution ---
def delete_all_trash_items(root_collection_id: int = 1):
    """
    Fetches all items recursively starting from a root collection (e.g., trash)
    and deletes them.
    """
    if not login():
        return # Stop if login fails

    logging.info(f"Starting recursive fetch from root collection ID: {root_collection_id}")
    all_items_to_delete = get_all_items_recursive(root_collection_id)

    if not all_items_to_delete:
        logging.info("No items found to delete.")
        return

    logging.info(f"Found {len(all_items_to_delete)} items (including nested) to delete.")
    # Optional: Print items before deleting for verification
    # print("Items to delete:")
    # for item in all_items_to_delete:
    #     print(f"  - {item['model']} (ID: {item['id']})")

    # Proceed with deletion
    delete_items(all_items_to_delete)
    logging.info("Deletion process finished.")


if __name__ == "__main__":
    # Assuming '1' is the ID for the root/trash collection you want to clear.
    # Adjust if your 'trash' or target collection has a different ID.
    # You might need to find this ID via the Metabase UI or another API call.
    TRASH_COLLECTION_ID = 1
    delete_all_trash_items(TRASH_COLLECTION_ID)
