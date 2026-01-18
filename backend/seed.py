from sqlmodel import Session, create_engine, select, SQLModel
from app.models.database import User, Region, Node
from app.core.security import get_password_hash
from app.core.config import settings

engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False}
    if settings.DATABASE_URL.startswith("sqlite")
    else {},
)

def seed():
    # Create tables if they don't exist
    SQLModel.metadata.create_all(engine)
    
    with Session(engine) as session:
        # 1. Create Regions (check if they exist)
        existing_regions = session.exec(select(Region)).all()
        if not existing_regions:
            r_us = Region(code="US", name="United States")
            r_mx = Region(code="MX", name="Mexico")
            r_pt = Region(code="PT", name="Portugal")
            session.add_all([r_us, r_mx, r_pt])
            session.commit()
            session.refresh(r_us)
            session.refresh(r_mx)
            session.refresh(r_pt)
        else:
            r_us = next(r for r in existing_regions if r.code == "US")
            r_mx = next(r for r in existing_regions if r.code == "MX")
            r_pt = next(r for r in existing_regions if r.code == "PT")
        
        # 2. Create Nodes (check if they exist)
        existing_nodes = session.exec(select(Node)).all()
        if not existing_nodes:
            n1 = Node(
                region_id=r_us.id,
                name="Miami-01",
                endpoint_host="miami.wg.example.com",
                server_public_key="SERVER_PUB_KEY_MIAMI",
                ipv4_pool_cidr="10.66.10.0/24",
                mt_host="192.168.1.10",
                mt_user="admin",
                mt_pass="admin",
                mt_api_port=8750
            )
            n2 = Node(
                region_id=r_mx.id,
                name="CDMX-01",
                endpoint_host="cdmx.wg.example.com",
                server_public_key="SERVER_PUB_KEY_MEXICO",
                ipv4_pool_cidr="10.66.20.0/24",
                mt_host="192.168.1.11",
                mt_user="admin",
                mt_pass="admin",
                mt_api_port=8750
            )
            session.add_all([n1, n2])
        
        # 3. Create Admin & Test User (check if they exist)
        existing_users = session.exec(select(User)).all()
        if not existing_users:
            admin = User(
                username="admin",
                password_hash=get_password_hash("admin123"),
                role="ADMIN"
            )
            user = User(
                username="user1",
                password_hash=get_password_hash("user123"),
                role="USER"
            )
            session.add_all([admin, user])
        
        session.commit()
        print("Database checked and seeded successfully!")

if __name__ == "__main__":
    seed()
