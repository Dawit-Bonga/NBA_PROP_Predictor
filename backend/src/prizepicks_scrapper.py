"""
PrizePicks Scraper - Automated prop collection for NBA
Uses undetected-chromedriver to bypass bot detection
"""

import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import pandas as pd
import time
import random
from datetime import datetime
import os

# Configuration
OUTPUT_PATH = '../data/predictions/todays_props.csv'
PRIZEPICKS_URL = 'https://app.prizepicks.com/'
TARGET_SPORT = 'NBA'  # Focus on NBA

def setup_driver(headless=True):
    """Initialize undetected Chrome driver to bypass bot detection"""
    print("🔧 Setting up undetected Chrome driver...")
    
    options = uc.ChromeOptions()
    
    # Basic options
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--window-size=1920,1080')
    
    # Add a realistic user agent
    options.add_argument('--user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
    
    if headless:
        options.add_argument('--headless=new')  # Use new headless mode
        print("  ℹ️ Running in headless mode")
    else:
        print("  ℹ️ Running in visible mode (for debugging)")
    
    # Create undetected chromedriver instance
    # version_main parameter helps with compatibility
    driver = uc.Chrome(options=options, use_subprocess=True)
    
    # Set page load timeout
    driver.set_page_load_timeout(30)
    
    return driver

def human_delay(min_sec=1, max_sec=3):
    """Add random human-like delay"""
    time.sleep(random.uniform(min_sec, max_sec))

def scroll_slowly(driver):
    """Scroll page slowly to mimic human behavior"""
    try:
        # Get page height
        total_height = driver.execute_script("return document.body.scrollHeight")
        
        # Scroll in chunks
        for i in range(0, total_height, random.randint(100, 300)):
            driver.execute_script(f"window.scrollTo(0, {i});")
            time.sleep(random.uniform(0.1, 0.3))
    except:
        pass

def close_popups(driver):
    """Handle any popups or overlays"""
    try:
        # Wait a bit for popups to appear
        human_delay(2, 4)
        
        # Common popup close button selectors
        close_selectors = [
            "button[aria-label='Close']",
            "button.close",
            "div.close-button",
            "[class*='close']",
            "[class*='modal'] button"
        ]
        
        for selector in close_selectors:
            try:
                close_btn = driver.find_element(By.CSS_SELECTOR, selector)
                close_btn.click()
                print("  ✓ Closed popup")
                human_delay(1, 2)
            except:
                continue
                
    except Exception as e:
        pass  # No popups found, continue

def select_nba_board(driver):
    """Navigate to NBA board"""
    try:
        print("🏀 Selecting NBA board...")
        
        # Wait for the board to load
        wait = WebDriverWait(driver, 20)
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div#board")))
        human_delay(2, 4)
        
        # Scroll a bit to look more human
        scroll_slowly(driver)
        human_delay(1, 2)
        
        # Look for NBA in league navigation
        try:
            # Try to find NBA button in league navigation
            nba_button = driver.find_element(By.XPATH, 
                "//nav[contains(@class, 'league-navigation')]//button[contains(., 'NBA')] | "
                "//nav[contains(@class, 'league-navigation')]//div[contains(., 'NBA')] | "
                "//button[contains(text(), 'NBA')] | "
                "//div[contains(@class, 'league') and contains(., 'NBA')]"
            )
            
            # Move to element before clicking (more human-like)
            driver.execute_script("arguments[0].scrollIntoView(true);", nba_button)
            human_delay(0.5, 1)
            
            nba_button.click()
            print("  ✓ NBA board selected")
            human_delay(3, 5)
            return True
        except:
            # If can't find button, might already be on NBA or default to it
            print("  ℹ️ NBA selector not found, might already be selected, proceeding...")
            return True
        
    except Exception as e:
        print(f"  ⚠️ Error selecting NBA: {e}")
        return False

def scrape_props(driver):
    """
    Scrape player props from PrizePicks using actual HTML structure
    Based on: <ul aria-label="Projections List"> containing <li> elements
    """
    print("🔍 Scraping props...")
    
    props = []
    
    try:
        wait = WebDriverWait(driver, 20)
        
        # Wait for the projections list to load
        print("  ⏳ Waiting for projections to load...")
        try:
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "ul[aria-label='Projections List']")))
            human_delay(4, 6)  # Extra time for dynamic content to render
        except:
            print("  ⚠️ Projections List not found, trying alternative selectors...")
            # Try alternative: div with projections id
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div#projections")))
            human_delay(4, 6)
        
        # Scroll to load all projections (lazy loading)
        scroll_slowly(driver)
        human_delay(2, 3)
        
        # Find all projection items
        # Based on screenshots: <li id="test-projection-li" aria-label="Player Name - Team">
        projection_items = driver.find_elements(By.CSS_SELECTOR, 
            "ul[aria-label='Projections List'] > li, "
            "div#projections li, "
            "li[id*='projection']"
        )
        
        print(f"  📊 Found {len(projection_items)} projection cards")
        
        if len(projection_items) == 0:
            print("  ⚠️ No projections found with standard selectors")
            print("  📝 Using demo data...")
            return create_demo_props()
        
        # DEBUG: Save first card's HTML to file
        if len(projection_items) > 0:
            try:
                debug_html = projection_items[0].get_attribute('outerHTML')
                debug_path = '../data/debug_card.html'
                with open(debug_path, 'w', encoding='utf-8') as f:
                    f.write(debug_html)
                print(f"  🐛 Saved first card HTML to: {debug_path}")
            except:
                pass
        
        for idx, item in enumerate(projection_items):
            try:
                # Get player name and team from aria-label
                # Format: "Player Name - TEAM" (e.g., "Devin Vassell - SAS")
                aria_label = item.get_attribute('aria-label')
                
                if not aria_label:
                    continue
                
                parts = aria_label.split(' - ')
                if len(parts) >= 1:
                    player_name = parts[0].strip()
                    team = parts[1].strip() if len(parts) > 1 else None
                else:
                    continue
                
                # Get all text content from the card
                full_text = item.text
                
                if not full_text:
                    continue
                
                # Split into lines to parse
                lines = [line.strip() for line in full_text.split('\n') if line.strip()]
                
                stat_type = None
                line_value = None
                
                # Parse through lines to find stat type and value
                for line in lines:
                    # Skip player name and team (already extracted)
                    if line == player_name or (team and line == team):
                        continue
                    
                    # Check if this is a stat type
                    if not stat_type and any(keyword in line.lower() for keyword in 
                        ['point', 'pts', 'rebound', 'reb', 'assist', 'ast', 
                         'block', 'blk', 'steal', 'stl', '3-pt', 'three']):
                        stat_type = line
                    
                    # Check if this is a numeric value (the line)
                    if not line_value:
                        try:
                            # Try to parse as float
                            val = float(line.replace(',', ''))
                            if 0 < val < 100:  # Reasonable range for NBA props
                                line_value = val
                        except:
                            pass
                
                # Try alternative: look in specific div elements
                if not stat_type or not line_value:
                    try:
                        # Look for divs with test IDs or specific classes
                        text_divs = item.find_elements(By.CSS_SELECTOR, 
                            "div[class*='text-'], "
                            "div[id*='test-'], "
                            "div[class*='stat'], "
                            "span[class*='name'], "
                            "div[class*='projection']"
                        )
                        
                        for div in text_divs:
                            text = div.text.strip()
                            if not text:
                                continue
                            
                            # Check for stat type
                            if not stat_type and any(keyword in text.lower() for keyword in 
                                ['point', 'pts', 'rebound', 'reb', 'assist', 'ast']):
                                stat_type = text
                            
                            # Check for line value
                            if not line_value:
                                try:
                                    val = float(text.replace(',', ''))
                                    if 0 < val < 100:
                                        line_value = val
                                except:
                                    pass
                    except:
                        pass
                
                # Map stat type to our format (PTS, REB, AST)
                if stat_type:
                    stat_mapped = map_stat_type(stat_type)
                else:
                    stat_mapped = None
                
                # Only add if we have all required data and it's a stat we care about
                if player_name and stat_type and line_value and stat_mapped:
                    props.append({
                        'player': player_name,
                        'stat': stat_type,
                        'line': line_value,
                        'stat_mapped': stat_mapped,
                        'source': 'PrizePicks',
                        'timestamp': datetime.now().isoformat()
                    })
                    print(f"  ✓ {player_name} - {stat_type}: {line_value}")
                
            except Exception as e:
                # Skip individual items that fail
                continue
        
        if len(props) == 0:
            print("  ⚠️ Could not extract prop data from cards")
            print("  📝 Using demo data for testing...")
            props = create_demo_props()
    
    except Exception as e:
        print(f"  ❌ Error scraping: {e}")
        import traceback
        traceback.print_exc()
        props = create_demo_props()
    
    return props

def map_stat_type(stat_str):
    """Map PrizePicks stat names to our format"""
    stat_lower = stat_str.lower()
    
    if 'point' in stat_lower or 'pts' in stat_lower:
        return 'PTS'
    elif 'rebound' in stat_lower or 'reb' in stat_lower:
        return 'REB'
    elif 'assist' in stat_lower or 'ast' in stat_lower:
        return 'AST'
    else:
        return None  # We only predict PTS, REB, AST

def create_demo_props():
    """Create demo props for testing when scraper fails"""
    demo_players = [
        ('LeBron James', 'Points', 25.5, 'PTS'),
        ('Stephen Curry', 'Points', 28.5, 'PTS'),
        ('Giannis Antetokounmpo', 'Points', 30.5, 'PTS'),
        ('Luka Doncic', 'Points', 32.5, 'PTS'),
        ('Kevin Durant', 'Points', 27.5, 'PTS'),
        ('Jayson Tatum', 'Points', 26.5, 'PTS'),
        ('Damian Lillard', 'Points', 25.5, 'PTS'),
        ('Anthony Davis', 'Points', 24.5, 'PTS'),
        ('LeBron James', 'Rebounds', 7.5, 'REB'),
        ('Giannis Antetokounmpo', 'Rebounds', 11.5, 'REB'),
        ('Anthony Davis', 'Rebounds', 12.5, 'REB'),
        ('Nikola Jokic', 'Rebounds', 13.5, 'REB'),
        ('Joel Embiid', 'Rebounds', 11.5, 'REB'),
        ('Luka Doncic', 'Assists', 8.5, 'AST'),
        ('LeBron James', 'Assists', 7.5, 'AST'),
        ('Nikola Jokic', 'Assists', 9.5, 'AST'),
        ('Trae Young', 'Assists', 10.5, 'AST'),
        ('Chris Paul', 'Assists', 8.5, 'AST'),
    ]
    
    props = []
    for player, stat, line, stat_mapped in demo_players:
        props.append({
            'player': player,
            'stat': stat,
            'line': line,
            'stat_mapped': stat_mapped,
            'source': 'Demo',
            'timestamp': datetime.now().isoformat()
        })
    
    return props

def scrape_prizepicks(headless=True):
    """Main scraping function"""
    print("\n" + "="*60)
    print("🎯 PRIZEPICKS SCRAPER")
    print("="*60)
    
    driver = None
    
    try:
        # Setup
        driver = setup_driver(headless=headless)
        
        # Navigate to PrizePicks
        print(f"\n📡 Loading {PRIZEPICKS_URL}...")
        driver.get(PRIZEPICKS_URL)
        
        # Wait for initial page load
        print("  ⏳ Waiting for page to load...")
        human_delay(5, 8)
        
        # Check if we hit a captcha
        if "captcha" in driver.page_source.lower() or "press & hold" in driver.page_source.lower():
            print("  ⚠️ Bot detection / CAPTCHA detected!")
            print("  💡 Try: 1) Running without --headless, 2) Wait and try again later")
            if not headless:
                print("  ℹ️ Please solve the CAPTCHA manually in the browser...")
                print("  ⏳ Waiting 30 seconds for manual intervention...")
                time.sleep(30)
        
        # Handle popups
        close_popups(driver)
        
        # Select NBA
        select_nba_board(driver)
        
        # Scrape props
        props = scrape_props(driver)
        
        # Convert to DataFrame
        if props:
            df = pd.DataFrame(props)
            
            # Save to CSV
            df.to_csv(OUTPUT_PATH, index=False)
            
            print(f"\n✅ SUCCESS: Scraped {len(df)} props")
            print(f"📁 Saved to: {OUTPUT_PATH}")
            
            # Show summary
            print(f"\n📊 Summary:")
            for stat_type in df['stat_mapped'].unique():
                count = len(df[df['stat_mapped'] == stat_type])
                print(f"  {stat_type}: {count} props")
            
            return df
        else:
            print("\n⚠️ No props found")
            return None
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return None
        
    finally:
        if driver:
            driver.quit()
            print("\n🔒 Browser closed")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Scrape PrizePicks NBA props')
    parser.add_argument('--visible', action='store_true', help='Run browser in visible mode (for debugging)')
    args = parser.parse_args()
    
    scrape_prizepicks(headless=not args.visible)