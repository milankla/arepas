"""
CSV parsing utilities for handling messy historical data files.
"""

import csv
from io import StringIO
from typing import List, Optional, Tuple, Dict, Any
import pandas as pd
from loguru import logger


class CSVParseError(Exception):
    """Custom exception for CSV parsing errors."""
    pass


class RobustCSVParser:
    """
    Handles robust CSV parsing with error recovery for historical data files.
    
    Features:
    - Graceful fallback parsing for malformed lines
    - Quote normalization (curly to straight quotes)
    - Comment line filtering
    - Configurable field tolerance
    """
    
    # Class constants
    COMMENT_PREFIX = '//'
    QUOTE_REPLACEMENTS: List[Tuple[str, str]] = [
        ('"', '"'), ('"', '"'), ('"', '"'),  # Curly quotes to straight
        (''', "'"), (''', "'")  # Curly apostrophes to straight
    ]
    DEFAULT_FIELD_TOLERANCE = 10
    
    def __init__(self, field_tolerance: Optional[int] = None):
        """
        Initialize parser with optional configuration.
        
        Args:
            field_tolerance: Maximum extra fields allowed beyond expected count.
                           Defaults to DEFAULT_FIELD_TOLERANCE (10).
        """
        self.field_tolerance = field_tolerance if field_tolerance is not None else self.DEFAULT_FIELD_TOLERANCE
    
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
            return self._parse_with_pandas(lines, strict=True)
        except Exception as e:
            logger.warning(f"Standard parsing failed: {e}")
            return self._parse_with_fallback(lines)
    
    def _clean_line(self, line: str) -> str:
        """Clean a single line by replacing problematic quotes."""
        cleaned = line.strip()
        for old, new in self.QUOTE_REPLACEMENTS:
            cleaned = cleaned.replace(old, new)
        return cleaned
    
    def _read_and_clean_file(self, file_path: str) -> List[str]:
        """Read file and perform basic cleaning."""
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = [line for line in f if not line.strip().startswith(self.COMMENT_PREFIX)]
        
        logger.debug(f"Read {len(lines)} lines (comments filtered)")
        
        # Clean lines by replacing problematic quotes
        clean_lines = [self._clean_line(line) for line in lines]
        return clean_lines
    
    def _get_pandas_config(self, strict: bool = True) -> Dict[str, Any]:
        """
        Get pandas read_csv configuration.
        
        Args:
            strict: If True, include error handling options
            
        Returns:
            Configuration dict for pd.read_csv
        """
        config = {
            'delimiter': '\t',
            'engine': 'python'
        }
        if strict:
            config.update({
                'on_bad_lines': 'skip',
                'quoting': csv.QUOTE_MINIMAL
            })
        return config
    
    def _parse_with_pandas(self, lines: List[str], strict: bool = True) -> pd.DataFrame:
        """
        Attempt standard pandas parsing.
        
        Args:
            lines: Cleaned lines to parse
            strict: Whether to use strict error handling
            
        Returns:
            Parsed DataFrame
        """
        return pd.read_csv(
            StringIO('\n'.join(lines)),
            **self._get_pandas_config(strict)
        )
    
    def _parse_with_fallback(self, lines: List[str]) -> pd.DataFrame:
        """
        Fallback parsing with manual line filtering.
        
        Args:
            lines: Lines to parse
            
        Returns:
            Parsed DataFrame
            
        Raises:
            CSVParseError: If parsing fails or invalid input
        """
        if not lines:
            raise CSVParseError("No lines to parse")
        if len(lines) < 2:
            raise CSVParseError("Need at least header and one data row")
        
        header_line = lines[0]
        data_lines = lines[1:]
        expected_cols = len(header_line.split('\t'))
        
        logger.info(f"Fallback parsing: {expected_cols} expected columns")
        
        filtered_lines = [header_line]
        skipped_count = 0
        
        for i, line in enumerate(data_lines, 1):
            if self._is_line_valid(line, expected_cols):
                filtered_lines.append(line)
            else:
                logger.debug(f"Skipping malformed line {i+1}")
                skipped_count += 1
        
        if skipped_count > 0:
            logger.warning(f"Skipped {skipped_count} malformed lines")
        logger.info(f"Filtered to {len(filtered_lines)} valid lines")
        
        try:
            return pd.read_csv(
                StringIO('\n'.join(filtered_lines)),
                **self._get_pandas_config(strict=False)
            )
        except Exception as e:
            raise CSVParseError(f"All parsing attempts failed: {e}")
    
    def _is_line_valid(self, line: str, expected_cols: int) -> bool:
        """
        Check if a line can be parsed and has reasonable field count.
        
        Args:
            line: Line to validate
            expected_cols: Expected number of columns
            
        Returns:
            True if line is valid, False otherwise
        """
        try:
            test_reader = csv.reader(StringIO(line), delimiter='\t', quotechar='"')
            fields = next(test_reader)
            field_count = len(fields)
            return field_count <= expected_cols + self.field_tolerance
        except Exception:
            return False
