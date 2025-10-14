# 🚀 Spaced Repetition Flashcard App

A full-stack web application designed to help users learn and retain information using an algorithm based on the principles of spaced repetition. The frontend is built with **Next.js** and the backend is powered by **FastAPI**.

---

## Live Application

The live application is running at [flashcards](https://hiring-eniola-arinde-flashcards.vercel.app)

1.  **Test login**

    ```sh
    Test email - test@flashcards.com
    password - flashcards
    ```

---

## Features

- **User Authentication**: Secure user signup and login using JWT (JSON Web Tokens).
- **Protected Routes**: Middleware ensures that only authenticated users can access the dashboard and study pages.
- **Admin Dashboard**: A central place to create new flashcards and view the status of all existing cards, including their current learning bin, incorrect answer count, and next review time.
- **Spaced Repetition Engine**: The core of the application, which intelligently schedules cards for review based on user performance.
- **Interactive Study Interface**: A clean, non-scrollable UI for focusing on one card at a time. Users can reveal the definition and mark their answers as correct or incorrect.
- **Dynamic Status Messages**: The app provides clear feedback when a study session is temporarily or permanently complete.

---

## Tech Stack

### Frontend

- **Framework**: [Next.js](https://nextjs.org/) (with App Router)
- **Language**: [TypeScript](https://www.typescriptlang.org/)
- **Styling**: [Tailwind CSS](https://tailwindcss.com/)
- **UI Components**: [shadcn/ui](https://ui.shadcn.com/) & [neobrutalism.dev](https://www.neobrutalism.dev/)
- **Form Management**: [React Hook Form](https://react-hook-form.com/) & [Zod](https://zod.dev/) for validation
- **Date Handling**: [date-fns](https://date-fns.org/)

### Backend

- **Framework**: [FastAPI](https://fastapi.tiangolo.com/)
- **Language**: [Python](https://www.python.org/)
- **Database**: PostgreSQL (or SQLite) with [SQLAlchemy](https://www.sqlalchemy.org/) ORM
- **Async Support**: [Uvicorn](https://www.uvicorn.org/) ASGI server

---

## Getting Started

Follow these instructions to get a copy of the project up and running on your local machine for development and testing purposes.

### Prerequisites

Make sure you have the following software installed:

- [Node.js](https://nodejs.org/en) (v18.x or later)
- [Python](https://www.python.org/downloads/) (v3.8 or later)
- [npm](https://www.npmjs.com/) or any other package manager like yarn or pnpm

### Installation & Setup

1.  **Clone the repository:**

    ```sh
    git clone [https://github.com/your-username/your-repo-name.git](https://github.com/your-username/your-repo-name.git)
    cd your-repo-name
    ```

2.  **Setup the Backend:**

    ```sh
    # Navigate to the backend directory
    cd backend

    # Create a virtual environment
    uv venv --python python-version
    source venv/bin/activate  # On Windows, use `venv\Scripts\activate`

    # Install Python dependencies
    uv install
    ```

3.  **Setup the Frontend:**

    ```sh
    # Navigate to the frontend directory from the root
    cd frontend

    # Install Node.js dependencies
    npm install
    ```

### Environment Variables

You'll need to create `.env` files for both the frontend and backend.

1.  **Backend `.env` file:**
    In the `/backend` directory, create a `.env` file and add the necessary variables.

    ```env
    # Example .env for the backend
    DATABASE_URL="postgresql://user:password@host:port/database_name"
    SECRET_KEY="your_super_secret_key_for_jwt"
    ALGORITHM="HS256"
    ```

2.  **Frontend `.env.local` file:**
    In the `/frontend` directory, create a `.env.local` file to point to your backend API.
    ```env
    # Example .env.local for the frontend
    NEXT_PUBLIC_API_BASE_URL="[http://127.0.0.1:8000](http://127.0.0.1:8000)"
    ```

### Running the Application

1.  **Start the Backend Server:**
    From the `/backend` directory (with your virtual environment activated):

    ```sh
    fastapi run src/app.py
    ```

    The backend API will be running at `http://127.0.0.1:8000`.

2.  **Start the Frontend Development Server:**
    From the `/frontend` directory in a new terminal window:
    ```sh
    npm run dev
    ```
    The frontend application will be accessible at `http://localhost:3000`.
