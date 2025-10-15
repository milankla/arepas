"""
CSV parsing utilities for handling messy historical data files.
"""

import csv
from io import StringIO
from typing import List, Optional
import re
import pandas as pd
from loguru import logger


class CSVParseError(Exception):
    """Custom exception for CSV parsing errors."""
    pass


class RobustCSVParser:
    """
    Handles robust CSV parsing with error recovery for historical data files.
    """
    
    def __init__(self, field_tolerance: int = 10, preview_length: int = 200):
        # Configurable constants (can be overridden)
        self.FIELD_TOLERANCE = field_tolerance  # Allow extra fields beyond expected
        self.PREVIEW_LENGTH = preview_length    # Characters to show in error previews
        
        self.quote_replacements = [
            ('"', '"'), ('"', '"'), ('"', '"'),  # Curly quotes to straight
            (''', "'"), (''', "'")  # Curly apostrophes to straight
        ]
    
    def parse_file(self, file_path: str) -> pd.DataFrame:
        """
        Parse a CSV file with robust error handling.
        
        Args:
            file_path: Path to the CSV file
            
        Returns:
            Parsed DataFrame
            
        Raises:
            CSVParseError: If all parsing attempts fail
        """
        logger.info(f"Parsing CSV file: {file_path}")
        
        try:
            lines = self._read_and_clean_file(file_path)
            return self._parse_with_pandas(lines)
        except Exception as e:
            logger.warning(f"Standard parsing failed: {e}")
            return self._parse_with_fallback(lines)
    
    def _read_and_clean_file(self, file_path: str) -> List[str]:
        """Read file and perform basic cleaning."""
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = [line for line in f if not line.strip().startswith('//')]
        
        # Replace problematic quotes
        clean_lines = []
        for line in lines:
            cleaned = line.strip()
            for old_char, new_char in self.quote_replacements:
                cleaned = cleaned.replace(old_char, new_char)
            clean_lines.append(cleaned)
        
        return clean_lines
    
    def _parse_with_pandas(self, lines: List[str]) -> pd.DataFrame:
        """Attempt standard pandas parsing."""
        return pd.read_csv(
            StringIO('\n'.join(lines)),
            delimiter='\t',
            engine='python',
            on_bad_lines='skip',
            quoting=csv.QUOTE_MINIMAL
        )
    
    def _parse_with_fallback(self, lines: List[str]) -> pd.DataFrame:
        """Fallback parsing with manual line filtering."""
        if not lines:
            raise CSVParseError("No lines to parse")
        
        header_line = lines[0]
        data_lines = lines[1:]
        expected_cols = len(header_line.split('\t'))
        
        logger.info(f"Expected columns: {expected_cols}")
        
        filtered_lines = [header_line]
        skipped_count = 0
        
        for i, line in enumerate(data_lines, 1):
            if self._is_line_valid(line, expected_cols):
                filtered_lines.append(line)
            else:
                logger.debug(f"Skipping malformed line {i+1}")
                skipped_count += 1
        
        logger.info(f"Filtered {len(lines)} to {len(filtered_lines)} lines (skipped {skipped_count})")
        
        try:
            return pd.read_csv(
                StringIO('\n'.join(filtered_lines)),
                delimiter='\t',
                engine='python'
            )
        except Exception as e:
            raise CSVParseError(f"All parsing attempts failed: {e}")
    
    def _is_line_valid(self, line: str, expected_cols: int) -> bool:
        """Check if a line can be parsed and has reasonable field count."""
        try:
            test_reader = csv.reader(StringIO(line), delimiter='\t', quotechar='"')
            fields = next(test_reader)
            field_count = len(fields)
            return field_count <= expected_cols + self.FIELD_TOLERANCE
        except Exception:
            return False
