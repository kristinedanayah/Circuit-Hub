# Circuit Hub

Circuit Hub is a Flask + Supabase IT marketplace/resource hub for IT students and IT teachers/instructors.

## Features
- Login and registration through Supabase Auth
- Student / Teacher-Instructor account types
- Product catalog
- Cart and checkout
- Orders stored in Supabase
- Wishlist-ready structure
- ₱500 Budget Finder
- Official software downloads
- Student/teacher-friendly design
- Render/GitHub-ready Flask structure

## Local setup

1. Create a Supabase project.
2. Run `supabase/schema.sql` in Supabase SQL Editor.
3. Copy `.env.example` to `.env`.
4. Put your Supabase Project URL and anon/publishable key in `.env`.
5. Open a terminal in this folder:
   `pip install -r requirements.txt`
6. Start:
   `python app.py`
7. Open:
   `http://127.0.0.1:5000`

Passwords are handled by Supabase Auth. Do not put service-role keys in this app.
