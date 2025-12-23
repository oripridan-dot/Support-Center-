import sys
import os

# Add the parent directory to sys.path to allow importing app modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlmodel import select
from app.core.database import get_session
from app.models.sql_models import Brand

def update_brands_local_logos():
    with next(get_session()) as session:
        # Update RCF
        rcf = session.exec(select(Brand).where(Brand.name == "RCF")).first()
        if rcf:
            rcf.logo_url = "/brands/rcf.svg"
            session.add(rcf)
            print(f"Updated RCF logo to {rcf.logo_url}")

        # Update Allen & Heath
        ah = session.exec(select(Brand).where(Brand.name.contains("Allen"))).first()
        if ah:
            ah.logo_url = "/brands/allen-heath.svg"
            session.add(ah)
            print(f"Updated Allen & Heath logo to {ah.logo_url}")

        # Update dBTechnologies
        db_tech = session.exec(select(Brand).where(Brand.name.contains("dB"))).first()
        if db_tech:
            db_tech.logo_url = "/brands/db-technologies.svg"
            session.add(db_tech)
            print(f"Updated dBTechnologies logo to {db_tech.logo_url}")

        session.commit()
        print("Brands updated successfully with local logos.")

if __name__ == "__main__":
    update_brands_local_logos()
