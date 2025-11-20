"""
Data models for migration tracking
"""
from dataclasses import dataclass
from typing import List
from utils import logger


@dataclass
class MigrationSummary:
    """Track migration statistics"""
    total_items: int = 0
    succeeded: int = 0
    failed: int = 0
    errors: List[str] = None
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []
    
    def add_success(self):
        self.total_items += 1
        self.succeeded += 1
    
    def add_failure(self, error_msg: str):
        self.total_items += 1
        self.failed += 1
        self.errors.append(error_msg)
    
    def print_summary(self):
        """Print migration summary report"""
        logger.info("\n" + "="*60)
        logger.info("MIGRATION SUMMARY")
        logger.info("="*60)
        logger.info(f"Total Items Attempted: {self.total_items}")
        logger.info(f"Succeeded: {self.succeeded}")
        logger.info(f"Failed: {self.failed}")
        if self.errors:
            logger.info(f"\nErrors ({len(self.errors)}):")
            for i, error in enumerate(self.errors, 1):
                logger.info(f"  {i}. {error}")
        logger.info("="*60 + "\n")

