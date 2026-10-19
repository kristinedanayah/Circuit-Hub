
import os
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()

url = os.getenv("SUPABASE_URL")
key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

if not url or not key:
    print("ERROR: Check your .env file.")
    print("Make sure SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY exist.")
    raise SystemExit

admin = create_client(url, key)

user_id = input("Paste your Supabase User UID: ").strip()

password = input("Enter your new password: ")
confirm = input("Confirm your new password: ")

if len(password) < 6:
    print("ERROR: Password must be at least 6 characters.")
    raise SystemExit

if password != confirm:
    print("ERROR: Passwords do not match.")
    raise SystemExit

try:
    result = admin.auth.admin.update_user_by_id(
        user_id,
        {"password": password}
    )

    if result.user:
        print("\nSUCCESS! Password updated successfully!")
        print("Now try logging in to Circuit Hub.")

    else:
        print("\nPassword update was not confirmed.")
        print("Check your Supabase dashboard.")

except Exception as e:
    print("\nPassword update failed:")
    print(str(e))
