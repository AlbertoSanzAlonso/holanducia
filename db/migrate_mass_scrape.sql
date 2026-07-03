-- Scraping masivo: cuota configurable desde la app
ALTER TABLE user_settings ADD COLUMN IF NOT EXISTS mass_scrape_target INTEGER DEFAULT 500;
ALTER TABLE user_settings ADD COLUMN IF NOT EXISTS mass_fb_scroll_steps INTEGER DEFAULT 100;
