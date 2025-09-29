import os
import json
import glob
import subprocess
import shutil

def clear_cache_and_credentials():
    """Clear the AWS CLI cache and credentials file."""

    cache_dir = os.path.expanduser("~/.aws/cli/cache")
    if os.path.exists(cache_dir):
        shutil.rmtree(cache_dir)
        print("AWS CLI cache cleared.")


    credentials_file = os.path.expanduser("~/.aws/credentials")
    if os.path.exists(credentials_file):
        os.remove(credentials_file)
        print("AWS credentials file cleared.")

def list_s3_buckets(profile_name):
    print(f"Listing S3 buckets for profile: {profile_name}")
    try:
        subprocess.run(["aws", "s3", "ls", "--profile", profile_name], check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error listing S3 buckets: {e}")
        raise

def aws_sso_login(profile_name):
    print(f"Logging in to AWS SSO using profile: {profile_name}")
    try:
        subprocess.run(["aws", "sso", "login", "--profile", profile_name], check=True)
        print("AWS SSO login successful.")
    except subprocess.CalledProcessError as e:
        print(f"Error during AWS SSO login: {e}")
        raise    
    try:
        list_s3_buckets(profile_name)
    except Exception as e:
        print(f"Failed to list S3 buckets: {e}")
        
def get_latest_sso_cache_file():
    """Find the latest SSO cache file in the AWS CLI cache directory."""

    cache_dir = os.path.expanduser("~/.aws/cli/cache")
    
    json_files = glob.glob(os.path.join(cache_dir, "*.json"))
    
    if not json_files:
        raise FileNotFoundError(f"No JSON cache files found in {cache_dir}. Please run 'aws sso login' first.")
    
    latest_file = max(json_files, key=os.path.getmtime)
    return latest_file

def extract_credentials_from_cache(cache_file):
    """Extract AWS credentials from the given SSO cache JSON file."""
    with open(cache_file, 'r') as file:
        cache_data = json.load(file)
    
    try:
        access_key_id = cache_data['Credentials']['AccessKeyId']
        secret_access_key = cache_data['Credentials']['SecretAccessKey']
        session_token = cache_data['Credentials']['SessionToken']
    except KeyError:
        raise KeyError("Could not find 'Credentials' in the cache file.")
    
    return access_key_id, secret_access_key, session_token

def write_credentials_to_file(profile_name, access_key_id, secret_access_key, session_token):
    """Write or update credentials for a specific profile in the AWS credentials file."""
    credentials_file = os.path.expanduser("~/.aws/credentials")
    
    os.makedirs(os.path.dirname(credentials_file), exist_ok=True)

    profiles = {}
    if os.path.exists(credentials_file):
        with open(credentials_file, 'r') as file:
            lines = file.readlines()
        
        current_profile = None
        for line in lines:
            if line.startswith('['):
                current_profile = line.strip()[1:-1]
            elif current_profile:
                if current_profile not in profiles:
                    profiles[current_profile] = []
                profiles[current_profile].append(line.strip())
        
    profiles[profile_name] = [
        f"aws_access_key_id = {access_key_id}",
        f"aws_secret_access_key = {secret_access_key}",
        f"aws_session_token = {session_token}"
    ]
            
    with open(credentials_file, 'w') as file:
        for profile, credentials in profiles.items():
            if profile == "sandbox":
                for sandbox_profile in ["sandbox", "sandbox2", "sandbox3"]:
                    file.write(f"[{sandbox_profile}]\n")
                    for credential in credentials:
                        file.write(f"{credential}\n")
                    file.write("\n")
            else:
                file.write(f"[{profile}]\n")
                for credential in credentials:
                    file.write(f"{credential}\n")
                file.write("\n")
        
    print(f"Credentials for profile '{profile_name}' have been written to {credentials_file}.")


def main():

    clear_cache_and_credentials()
    
    profiles = ["shared","dev", "sandbox"]

    for profile_name in profiles:

        try:
            aws_sso_login(profile_name)
        except Exception as e:
            print(f"Login failed: {e}")
            return

        try:
            cache_file = get_latest_sso_cache_file()
            print(f"Found cache file: {cache_file}")
        except FileNotFoundError as e:
            print(e)
            return
        
        try:
            access_key_id, secret_access_key, session_token = extract_credentials_from_cache(cache_file)
            print("Credentials extracted successfully.")
        except KeyError as e:
            print(e)
            return
        
        write_credentials_to_file("default" if profile_name == "shared" else profile_name, access_key_id, secret_access_key, session_token)

if __name__ == "__main__":
    main()
