"""
Example demonstrating the internal console system in OPAQUE Framework.

This example shows how to:
1. Add the console feature to your application
2. Capture stdout/stderr output automatically
3. Use the console for debugging and monitoring
4. Programmatically write to the console

@copyright 2025 Sandro Fadiga
Licensed under MIT License
"""

from PySide6.QtWidgets import QApplication
import sys
import time
import threading
from pathlib import Path

# Add both src and project root to Python path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root / "src"))
sys.path.insert(0, str(project_root))

try:
    from opaque.view.application import BaseApplication
    from opaque.presenters.console_presenter import ConsolePresenter
    from opaque.models.console_model import ConsoleModel
    from opaque.view.widgets.console_widget import ConsoleView
    from opaque.models.configuration import DefaultApplicationConfiguration
    from PySide6.QtGui import QIcon
except ImportError as e:
    print(f"Error importing OPAQUE modules: {e}")
    print("Make sure you're running this from the project root directory")
    sys.exit(1)

# Import QApplication


class ConsoleExampleConfiguration(DefaultApplicationConfiguration):
    """Configuration for the console example application."""

    def get_application_name(self) -> str:
        return "ConsoleExample"

    def get_application_title(self) -> str:
        return "OPAQUE Console Example"

    def get_application_description(self) -> str:
        return "Demonstration of OPAQUE Framework internal console system"

    def get_application_organization(self) -> str:
        return "OPAQUE Framework"

    def get_application_icon(self) -> QIcon:
        return QIcon()  # Use default icon


class ConsoleExampleApp(BaseApplication):
    """Example application demonstrating console functionality."""

    def __init__(self, config: ConsoleExampleConfiguration):
        super().__init__(config)
        self.console_presenter = None
        self.demo_thread = None
        self.demo_running = False

        # Initialize features after the application is set up
        self._setup_console()
        self._setup_demo_features()
        self._start_console_demo()

    def _setup_console(self):
        """Set up the internal console feature."""
        try:
            # Create console components
            console_model = ConsoleModel(self)
            self.console_presenter = ConsolePresenter(console_model, self)

            # Register the console feature with MDI area (this also adds toolbar button)
            self.register_feature(self.console_presenter)

            # Initialize the console (this starts capturing stdout/stderr)
            self.console_presenter.initialize()

            print("Console system initialized successfully!")
            print("This message should appear in the console window.")

        except Exception as e:
            print(f"Error setting up console: {e}")
            import traceback
            traceback.print_exc()

    def _setup_demo_features(self):
        """Set up additional features for demonstration."""
        # Skip demo features for now to avoid complexity
        print("Demo features skipped - focusing on console functionality")
        print("You can extend this example to add more features as needed")

    def _start_console_demo(self):
        """Start a background thread that generates sample output."""
        self.demo_running = True
        self.demo_thread = threading.Thread(
            target=self._console_demo_worker, daemon=True)
        self.demo_thread.start()

    def _console_demo_worker(self):
        """Worker thread that generates sample console output."""
        counter = 0

        while self.demo_running:
            try:
                time.sleep(3)  # Wait 3 seconds between outputs

                counter += 1

                if counter % 3 == 1:
                    # Normal stdout output
                    print(
                        f"[Demo] Regular output #{counter} - Everything is working normally")

                elif counter % 3 == 2:
                    # Error output to stderr
                    print(
                        f"[Demo] Simulated error #{counter} - This is an example error", file=sys.stderr)

                else:
                    # Programmatic output through console presenter
                    if self.console_presenter:
                        self.console_presenter.write_to_console(
                            f"[Demo] Programmatic output #{counter} - Written directly to console\n",
                            'stdout'
                        )

                # Occasionally generate multi-line output
                if counter % 5 == 0:
                    print("Multi-line output example:")
                    print("  Line 1: This demonstrates")
                    print("  Line 2: how multi-line output")
                    print("  Line 3: appears in the console")

                # Stop after 50 iterations to avoid endless spam
                if counter >= 50:
                    print("[Demo] Console demo completed - no more automatic output")
                    break

            except Exception as e:
                print(f"Demo worker error: {e}")
                break

    def closeEvent(self, event):
        """Handle application close event."""
        # Stop the demo thread
        self.demo_running = False
        if self.demo_thread and self.demo_thread.is_alive():
            self.demo_thread.join(timeout=1.0)

        # Clean up console
        if self.console_presenter:
            self.console_presenter.cleanup()

        super().closeEvent(event)


def demonstrate_console_features():
    """Demonstrate various console features programmatically."""
    print("\n=== Console Feature Demonstration ===")
    print("1. This is normal stdout output")
    print("2. You should see timestamps if enabled")

    # Generate stderr output
    print("3. This is stderr output (should appear in red)", file=sys.stderr)

    # Generate some structured output
    print("\n4. Structured output example:")
    data = {
        "timestamp": time.time(),
        "status": "running",
        "features": ["console", "logging", "calculator"]
    }
    print(f"   Data: {data}")

    # Simulate some processing with output
    print("\n5. Simulating processing...")
    for i in range(3):
        time.sleep(0.5)
        print(f"   Step {i+1}/3 completed")

    print("6. Processing complete!")

    # Show error handling
    print("\n7. Demonstrating error handling:")
    try:
        # This will cause an error
        result = 10 / 0
    except ZeroDivisionError as e:
        print(f"   Caught error: {e}", file=sys.stderr)

    print("\n8. Console demonstration finished!")
    print("   Try using the console toolbar buttons:")
    print("   - Clear: Clear all console output")
    print("   - Export: Save console output to file")
    print("   - Search: Find text in console output")
    print("   - Checkboxes: Filter what's displayed")


def main():
    """Main application entry point."""
    try:
        # Create QApplication instance first
        qt_app = QApplication(sys.argv)

        # Create configuration
        config = ConsoleExampleConfiguration()

        # Create the application window
        app = ConsoleExampleApp(config)

        # Set window title
        app.setWindowTitle("OPAQUE Console Example")

        # Show the application
        app.show()

        # Generate some initial demo output
        demonstrate_console_features()

        # Print usage instructions
        print("\n" + "="*60)
        print("CONSOLE EXAMPLE USAGE INSTRUCTIONS")
        print("="*60)
        print("1. Click 'Console' in the toolbar to open the console window")
        print("2. The console captures all stdout/stderr output automatically")
        print("3. Use toolbar buttons to:")
        print("   - Clear output")
        print("   - Export to file")
        print("   - Search through output")
        print("   - Filter by stdout/stderr")
        print("   - Toggle timestamps")
        print("4. The demo generates sample output every 3 seconds")
        print("5. Try opening other features (Calculator, Logging) to see their output")
        print("="*60)

        # Run the application
        return qt_app.exec()

    except Exception as e:
        print(f"Error starting application: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
