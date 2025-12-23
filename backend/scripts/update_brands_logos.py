import sys
import os

# Add the parent directory to sys.path to allow importing app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlmodel import select
from app.core.database import get_session
from app.models.sql_models import Brand

def update_brands():
    with next(get_session()) as session:
        # Update RCF
        rcf = session.exec(select(Brand).where(Brand.name == "RCF")).first()
        if not rcf:
            print("Creating RCF brand...")
            rcf = Brand(name="RCF", website_url="https://www.rcf.it")
            session.add(rcf)
        
        rcf.logo_url = "https://www.rcf.it/o/rcf-theme/images/logo.svg"
        session.add(rcf)
        print(f"Updated RCF logo to {rcf.logo_url}")

        # Update Allen & Heath
        ah = session.exec(select(Brand).where(Brand.name.contains("Allen"))).first()
        if not ah:
            print("Creating Allen & Heath brand...")
            ah = Brand(name="Allen & Heath", website_url="https://www.allen-heath.com")
            session.add(ah)
        else:
            print(f"Found Allen & Heath brand: {ah.name}")
            if ah.name != "Allen & Heath":
                ah.name = "Allen & Heath"
        
        ah.logo_url = "https://www.allen-heath.com/wp-content/themes/allen-heath/assets/images/ah-logo.svg"
        session.add(ah)
        print(f"Updated Allen & Heath logo to {ah.logo_url}")

        # Update dBTechnologies
        db_tech = session.exec(select(Brand).where(Brand.name.contains("dB"))).first()
        if not db_tech:
            print("Creating dBTechnologies brand...")
            db_tech = Brand(name="dBTechnologies", website_url="https://www.dbtechnologies.com")
            session.add(db_tech)
        
        db_tech.logo_url = "https://www.dbtechnologies.com/assets/img/logo.svg" # Hypothetical URL, or I can use a placeholder
        # Better URL: https://upload.wikimedia.org/wikipedia/commons/thumb/a/a6/DBTechnologies_logo.svg/2560px-DBTechnologies_logo.svg.png
        # Or check their site.
        # Let's use a generic one or try to find a real one.
        # https://www.dbtechnologies.com/qrcode/logo.png
        db_tech.logo_url = "https://www.dbtechnologies.com/qrcode/logo.png"
        session.add(db_tech)
        print(f"Updated dBTechnologies logo to {db_tech.logo_url}")

        session.commit()
        print("Brands updated successfully.")

if __name__ == "__main__":
    update_brands()
