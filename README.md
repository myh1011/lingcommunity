# Page Service Project

This project is a web application that allows users to create and manage pages. Each page consists of a title, body content, and a user-specified URL. The application provides an API for creating, deleting, and retrieving pages, with all data stored in a database.

## Project Structure

```
page-service
├── app
│   ├── main.py                # Entry point for the application, starts the server and configures routes.
│   ├── api
│   │   └── v1
│   │       ├── pages.py       # Defines API endpoints for page creation, deletion, and retrieval.
│   │       └── __init__.py    # Initializes the API module.
│   ├── models
│   │   ├── page.py            # Defines the page model with title, body, and URL.
│   │   └── __init__.py        # Initializes the models module.
│   ├── schemas
│   │   └── page.py            # Defines serialization and deserialization schemas for pages.
│   ├── db
│   │   ├── database.py        # Manages database connection and configuration.
│   │   └── migrations
│   │       └── README.md      # Instructions for database migrations.
│   ├── services
│   │   └── page_service.py     # Contains business logic for page operations.
│   ├── templates
│   │   ├── index.html         # HTML template for the homepage to create or view pages.
│   │   └── page.html          # HTML template for displaying a specific page's content.
│   └── static
│       ├── css
│       │   └── styles.css     # Stylesheet defining the appearance of the pages.
│       └── js
│           └── app.js         # Frontend JavaScript for handling user interactions and API requests.
├── tests
│   └── test_pages.py          # Unit tests for the page API to ensure functionality.
├── requirements.txt           # Lists the required Python dependencies for the project.
├── .env.example               # Example environment variables, including database connection info.
├── Dockerfile                 # Defines the environment for building the Docker image.
└── README.md                  # Documentation and usage instructions for the project.
```

## Getting Started

1. **Clone the repository**:
   ```
   git clone <repository-url>
   cd page-service
   ```

2. **Install dependencies**:
   ```
   pip install -r requirements.txt
   ```

3. **Set up the environment**:
   Copy `.env.example` to `.env` and configure your database connection and other settings.

4. **Run the application**:
   ```
   python app/main.py
   ```

5. **Access the API**:
   The API endpoints for creating, deleting, and retrieving pages are available at `/api/v1/pages`.

## Contributing

Contributions are welcome! Please open an issue or submit a pull request for any improvements or bug fixes.

## License

This project is licensed under the MIT License. See the LICENSE file for details.