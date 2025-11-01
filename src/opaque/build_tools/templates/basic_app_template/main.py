#!/usr/bin/env python3
"""
Basic OPAQUE Framework Application Template

This template provides a minimal starting point for creating OPAQUE framework
applications with executable building capabilities.

@copyright 2025 Your Name
Licensed under MIT License
"""

import sys
import logging
from pathlib import Path

from opaque.view.application import Application
from opaque.models.app_model import AppModel
from opaque.presenters.app_presenter import AppPresenter
from opaque.view.app_view import AppView


def setup_logging():
    """Setup basic logging configuration."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout),
            logging.FileHandler('app.log')
        ]
    )


def main():
    """Main application entry point."""
    try:
        # Setup logging
        setup_logging()
        logger = logging.getLogger(__name__)
        logger.info("Starting OPAQUE application...")

        # Create and run the application
        app = Application(sys.argv)

        # Setup MVP components
        model = AppModel()
        view = AppView()
        presenter = AppPresenter(model, view)

        # Configure main window
        view.setWindowTitle("My OPAQUE Application")
        view.resize(800, 600)
        view.show()

        logger.info("Application initialized successfully")

        # Start the application event loop
        return app.exec()

    except Exception as e:
        logging.error(f"Application startup failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
