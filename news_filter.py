"""
LIGHTWEIGHT NEWS FILTER MODULE
Uses the official ForexFactory weekly XML feed (no scraping required).
"""

import logging
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
import requests

logger = logging.getLogger(__name__)

class NewsFilter:
    def __init__(self, blackout_minutes=30, impact_levels=None):
        self.blackout_minutes = blackout_minutes
        self.impact_levels = impact_levels or ['high']  # Default to only high-impact
        self.cached_events = None
        self.last_fetch_time = None
        self.cache_duration = timedelta(hours=1)  # Refresh cache every hour

    def _fetch_calendar(self):
        """
        Fetch the official ForexFactory weekly XML feed.
        Uses the stable XML feed and correctly parses AM/PM times.
        """
        try:
            url = "https://nfs.faireconomy.media/ff_calendar_thisweek.xml"
            logger.info("Fetching economic calendar from official XML feed...")
            response = requests.get(url, timeout=10)
            response.raise_for_status()

            root = ET.fromstring(response.content)
            events = []

            for event_elem in root.findall('event'):
                title = event_elem.find('title').text if event_elem.find('title') is not None else ''
                country = event_elem.find('country').text if event_elem.find('country') is not None else ''
                impact = event_elem.find('impact').text if event_elem.find('impact') is not None else ''

                date_str = event_elem.find('date').text if event_elem.find('date') is not None else ''
                time_str = event_elem.find('time').text if event_elem.find('time') is not None else ''

                if not date_str or not time_str:
                    continue

                # Convert impact
                if impact == 'High':
                    impact_level = 'high'
                elif impact == 'Medium':
                    impact_level = 'medium'
                else:
                    impact_level = 'low'

                # Parse datetime (format: "04-23-2026" and "08:30am")
                try:
                    month, day, year = map(int, date_str.split('-'))

                    # ---- Fix: check AM/PM before removing them ----
                    raw_time = time_str.lower().strip()
                    is_pm = 'pm' in raw_time
                    is_am = 'am' in raw_time

                    clean_time = raw_time.replace('am', '').replace('pm', '').strip()
                    hour, minute = map(int, clean_time.split(':'))

                    if is_pm and hour != 12:
                        hour += 12
                    elif is_am and hour == 12:
                        hour = 0

                    event_time = datetime(year, month, day, hour, minute)
                except (ValueError, AttributeError):
                    continue

                events.append({
                    'datetime': event_time,
                    'currency': country.upper(),
                    'impact': impact_level,
                    'event': title
                })

            logger.info(f"Fetched {len(events)} economic events from XML feed.")
            return events

        except Exception as e:
            logger.error(f"Failed to fetch XML calendar: {e}")
            return []

    def _get_events(self):
        """Return cached events, refreshing if necessary."""
        now = datetime.now()
        if (self.cached_events is None or 
            self.last_fetch_time is None or 
            now - self.last_fetch_time > self.cache_duration):
            self.cached_events = self._fetch_calendar()
            self.last_fetch_time = now
        return self.cached_events

    def is_high_impact_nearby(self, pair):
        """
        Check if a high-impact news event is within the blackout window.
        """
        events = self._get_events()
        if not events:
            return False
        
        # Determine which currencies to check
        currencies_to_check = set()
        if len(pair) == 6:
            currencies_to_check = {pair[:3], pair[3:]}
        else:
            currencies_to_check = {pair[:3], pair[3:6]}
        
        now = datetime.now()
        blackout_start = now
        blackout_end = now + timedelta(minutes=self.blackout_minutes)
        
        for event in events:
            # Check impact level
            if event['impact'] not in self.impact_levels:
                continue
            
            # Check currency relevance
            if event['currency'] not in currencies_to_check:
                continue
            
            # Check time proximity
            event_time = event['datetime']
            if blackout_start <= event_time <= blackout_end:
                logger.info(f"⛔ High-impact news nearby: {event['event']} ({event['currency']}) at {event_time}")
                return True
        
        return False

    def get_upcoming_events(self, hours_ahead=6):
        """
        Get a list of upcoming high-impact events for logging/debugging.
        """
        events = self._get_events()
        if not events:
            return []
        
        now = datetime.now()
        future = now + timedelta(hours=hours_ahead)
        
        upcoming = []
        for event in events:
            event_time = event['datetime']
            if event_time >= now and event_time <= future:
                if event['impact'] in self.impact_levels:
                    upcoming.append(event)
        
        # Sort by time
        upcoming.sort(key=lambda x: x['datetime'])
        return upcoming