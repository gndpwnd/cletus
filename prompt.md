(venv) dev@DB-78GB094:~/cletus/new_app$ tree -I "__pycache__" -I "venv"
.
├── api
│   ├── analysis.py
│   ├── articles.py
│   ├── blacklist.py
│   └── scraper.py
├── blacklists
│   └── blklst_2025_10_10.json
├── cletus.db
├── core
│   ├── config.py
│   ├── database.py
│   └── sources.py
├── css_loader.py
├── logs
├── main.py
├── models
│   ├── __init_.py
│   └── models.py
├── requirements.txt
├── schemas
│   ├── __init__.py
│   ├── analysis_schemas.py
│   ├── article_schemas.py
│   ├── blacklist_schemas.py
│   └── scraper_schemas.py
├── services
│   ├── analysis_service.py
│   ├── blacklist_service.py
│   ├── scheduler_service.py
│   └── scraper_service.py
├── static
│   ├── css
│   │   ├── analysis.css
│   │   ├── animation.css
│   │   ├── articles.css
│   │   ├── base.css
│   │   ├── blacklist.css
│   │   ├── components.css
│   │   ├── layout.css
│   │   ├── navigation.css
│   │   ├── reset.css
│   │   ├── responsive.css
│   │   ├── scraper.css
│   │   ├── tables.css
│   │   ├── typography.css
│   │   ├── utilities.css
│   │   └── variables.css
│   └── js
│       ├── analysis.js
│       ├── articles.js
│       ├── blacklist.js
│       ├── dashboard.js
│       ├── main.js
│       ├── scraper.js
│       └── utils.js
└── templates
    ├── analysis.html
    ├── articles.html
    ├── base.html
    ├── blacklist.html
    ├── index.html
    └── scraper.html

11 directories, 51 files
(venv) dev@DB-78GB094:~/cletus/new_app$



ok, now i want to work on my analysis section, instead of detecting duplicates (which should already be happening when scraping), i want to have trending keywords for the past 24 hours, 48 hours, week, and month. I then want the ability to click on the keyword as if it were a hyperlink and have a drop down of all articles associated with it. OR what about this, when clicking on a keyword, i would be taken back to the articles search page with the search bar auto populated with that keyword? wouldn't that be snazzy? and it uses features i already have in place to save time.

ok, so analyze trends and have instead of detect duplicated tab, trending keywords across 24hrs, 48hrs, 7days, and 30days. then when clicking on that key word section header or element, be taken to a new tab that is the search page for the app with the search bar autopoluated with the key word. would it be easier to add an api enpoint to the search api? or not...

let me know if you want to view more files.