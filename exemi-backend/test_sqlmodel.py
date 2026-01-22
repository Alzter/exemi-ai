from fastapi import Depends, FastAPI, HTTPException, Query
from sqlmodel import Field, Relationship, Session, SQLModel, create_engine, select

class TeamBase(SQLModel):
    name : str = Field(index=True, max_length=255)
    headquarters : str = Field(max_length=255)

class Team(TeamBase, table=True):
    id : int | None = Field(default=None, primary_key=True)
    
    # 
    heroes : list["Hero"] = Relationship(back_populates="team")

class TeamCreate(TeamBase):
    pass

class TeamPublic(TeamBase):
    id : int

class TeamUpdate(SQLModel):
    name : str | None = None
    headquarters : str | None = None

class HeroBase(SQLModel):
    name : str = Field(index=True,max_length=255)
    secret_name : str = Field(max_length=255)
    age : int | None = Field(default=None)
    team_id : int | None = Field(default=None, foreign_key="team.id")

# Heroes in the database shall have an ID number,
# but manual assignment is optional thanks to auto-increment
class Hero(HeroBase, table=True):
    id : int | None = Field(default=None, primary_key=True)
    hashed_password : str = Field(max_length=255)
    team : Team | None = Relationship(back_populates="heroes")

# The HeroCreate class does not require any ID number
# since the server should handle ID assigning to Heroes.
class HeroCreate(HeroBase):
    password : str

# Heroes returned from the API shall have an ID number.
class HeroPublic(HeroBase):
    id : int
    hashed_password : str

# When making changes to a Hero, all fields are optional
class HeroUpdate(SQLModel):
    name : str | None = None
    secret_name : str | None = None
    age : int | None = None
    password : str | None = None
    team_id : int | None = None

class HeroPublicWithTeam(HeroPublic):
    team: TeamPublic | None = None

class TeamPublicWithHeroes(TeamPublic):
    heroes : list[HeroPublic] = []

url = "mariadb+mariadbconnector://root:root@127.0.0.1:3306/test"
engine = create_engine(url, echo=True)

def create_db_and_tables():
    SQLModel.metadata.create_all(engine)

def get_session():
    with Session(engine) as session:
        yield session

app = FastAPI()

@app.on_event("startup")
def on_startup():
    create_db_and_tables()

def fake_hash_password(password : str) -> str:
    return "hashed " + password

@app.post("/teams/", response_model=TeamPublicWithHeroes)
def create_team(team:TeamCreate, session: Session = Depends(get_session)):
    # Convert the TeamCreate object into a Team object.
    # Note: model_validate is basically from_dict().
    db_team = Team.model_validate(team)
    session.add(db_team)
    session.commit()
    session.refresh(db_team)
    return db_team

@app.get("/teams/", response_model=list[TeamPublic])
def read_teams(offset : int = 0, limit : int = Query(default=100, le=100), session : Session = Depends(get_session)):
    teams = session.exec(
        select(Team).offset(offset).limit(limit)
    ).all()
    return teams

@app.get("/teams/{team_id}", response_model=TeamPublicWithHeroes)
def read_team(team_id : int, session : Session = Depends(get_session)):
    team = session.get(Team, team_id)
    if not team: raise HTTPException(status_code=404, detail="Team not found")
    return team

@app.patch("/teams/{team_id}", response_model=TeamPublicWithHeroes)
def update_team(team_id : int, team : TeamUpdate, session : Session = Depends(get_session)):
    db_team = session.get(Team, team_id)
    if not db_team: raise HTTPException(status_code=404, detail="Team not found")
    team_data = team.model_dump(exclude_unset=True)
    db_team.sqlmodel_update(team_data)
    session.add(db_team)
    session.commit()
    session.refresh(db_team)
    return db_team

@app.delete("/teams/{team_id}")
def delete_team(team_id : int, session : Session = Depends(get_session)):
    team = session.get(Team, team_id)
    if not team: raise HTTPException(status_code=404, detail="Team not found")
    session.delete(team)
    session.commit()
    return {"ok":True}

@app.post("/heroes/", response_model=HeroPublicWithTeam)
def create_hero(hero : HeroCreate, session : Session = Depends(get_session)):
    hashed_password = fake_hash_password(hero.password)
    extra_data = {"hashed_password" : hashed_password}
    db_hero = Hero.model_validate(hero, update=extra_data)
    session.add(db_hero)
    session.commit()
    session.refresh(db_hero)
    return db_hero

@app.get("/heroes/", response_model=list[HeroPublic])
def read_heroes(offset : int = 0, limit : int = Query(default=100,le=100), session : Session = Depends(get_session)):
    heroes = session.exec(
        select(Hero).offset(offset).limit(limit)
    ).all()
    return heroes

@app.get("/heroes/{hero_id}", response_model=HeroPublicWithTeam)
def read_hero(hero_id : int, session : Session = Depends(get_session)):
    hero = session.get(Hero, hero_id)
    if not hero: raise HTTPException(status_code=404, detail="Hero not found")
    return hero

@app.patch("/heroes/{hero_id}", response_model=HeroPublicWithTeam)
def update_hero(hero_id:int, hero:HeroUpdate, session : Session = Depends(get_session)):
    db_hero = session.get(Hero, hero_id)
    if not db_hero: raise HTTPException(status_code=404, detail="Hero not found")
    
    # Convert all the HeroUpdate attributes into a dict.
    # Ignore all attributes which are None.
    hero_data = hero.model_dump(exclude_unset=True)
    
    extra_data = {}
    if "password" in hero_data:
        password = hero_data["password"]
        hashed_password = fake_hash_password(password)
        extra_data["hashed_password"] = hashed_password

    # Overwrite the attributes of the Hero in the DB
    # with the new attributes.
    db_hero.sqlmodel_update(hero_data, update=extra_data)
    
    # Commit, push upstream, pull.
    session.add(db_hero)
    session.commit()
    session.refresh(db_hero)
    return db_hero

@app.delete("/heroes/{hero_id}")
def delete_hero(hero_id : int, session : Session = Depends(get_session)):
    hero = session.get(Hero, hero_id)
    if not hero: raise HTTPException(status_code=404, detail="Hero not found")
    session.delete(hero)
    session.commit()
    return {"ok" : True}
