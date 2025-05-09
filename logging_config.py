# logging_config.py
import logging

def setup_logging():
    """Configures basic logging for the application."""
    logging.basicConfig(
        level=logging.INFO, # Default logging level
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler() # Log to console
            # Add a file handler if you want logs saved to a file
            # logging.FileHandler('edinet_tools.log')
        ]
    )
    # Optional: Set level for specific loggers if needed
    # logging.getLogger('httpx').setLevel(logging.WARNING) # Suppress noisy logs from httpx
