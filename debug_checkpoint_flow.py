import os
from typing import Dict, List, Literal, Optional, Annotated
from uuid import uuid4
import psycopg
from dotenv import load_dotenv

load_dotenv()

from pydantic import BaseModel, EmailStr, Field, SecretStr 
from langgraph.graph import StateGraph, START, END
from app.custom_encryption import SimpleEncryptedPostgresSaver


required_fields={"name", "email", "pan"}
class RegistrationState(BaseModel):
    name: str = Field(..., description="User's full name")
    email: EmailStr 
    phone: Optional[str] = Field(default=None, description="10 digit phone number" )
    dob: Optional[str] = Field(default= None, description="DD-MM-YYYY")
    pan: str = Field(...,description="Permanent Account Number")

    validation_errors: Dict[str,str] = Field(default_factory=dict)
    missing_fields: List[str] =  Field(default_factory=list)

    class Config:
        arbitrary_types_allowed = True


def collect_input(state: RegistrationState, patch: dict) -> RegistrationState:

    for k, v in patch.items():
        if hasattr(state, k):
            setattr(state, k, v)
    
    return state

def validate_present_fields(state: RegistrationState) -> RegistrationState:
    errors: Dict[str,str] = {}

    if state.name is not None:
        if len(state.name.strip()) <2:
            errors["name"] = "Name must be atleast 2 characters"


    if state.phone is not None:
        p = state.phone.strip()
        if not (p.isdigit() and len(p) == 10):
            errors["phone"] = "Phone must be exactly 10 digits."

    if state.dob is not None:
        parts = state.dob.split("-")
        if not (len(parts) == 3 and all(part.isdigit() for part in parts)):
            errors["dob"] = "DOB must be in DD-MM-YYYY format."

    if state.pan is not None:
        pan = state.pan.strip().upper()
        if len(pan) != 10:
            errors["pan"] = "PAN must be 10 characters."


    state.validation_errors = errors
    return state


def compute_missing_fields(state: RegistrationState) -> RegistrationState:
    missing = []

    for field in required_fields:
        val = getattr(state, field, None)
        if val is None:
            missing.append(field)
            continue
        if isinstance(val, str) and val.strip() == "":
            missing.append(field)
            continue

    for field in state.validation_errors.keys():
        if field not in missing:
            missing.append(field)

    state.missing_fields = sorted(missing)
    return state


def should_complete(state: RegistrationState) -> Literal["end", "complete"]:
    return "complete" if len(state.missing_fields) == 0 else "end"


def registration_complete(state: RegistrationState) -> RegistrationState:
    return state

def collect_node(state: RegistrationState)-> RegistrationState:
    return state

def build_graph():
    g = StateGraph(RegistrationState)
    
    g.add_node("collect", collect_node)
    g.add_node("validate", validate_present_fields)
    g.add_node("missing", compute_missing_fields)
    g.add_node("complete", registration_complete)

    g.add_edge(START, "collect")
    g.add_edge("collect", "validate")
    g.add_edge("validate", "missing")

    g.add_conditional_edges("missing", should_complete, {"end": END, "complete": "complete"})
    g.add_edge("complete", END)

    return g


def run_demo():
    conn_params = {
        "host": os.environ["PG_HOST"],
        "port": int(os.environ["PG_PORT"]),
        "dbname": os.environ["PG_DB"],
        "user": os.environ["PG_USER"],
        "password": os.environ["PG_PASSWORD"],
    }

    thread_id = "reg_demo_1"
    config = {"configurable": {"thread_id": thread_id}}

    patches = [
        {
            "name": "K",
            "email": "khushi@gmail.com",
            "pan": "ABCDE1234"
        },
        {
            "name": "Khushi",
            "pan": "ABCDE1234F"
        },
        {
            "phone": "9999999999",
            "dob": "01-01-2004",
        }
    ]


    conn = psycopg.connect(**conn_params)
    conn.autocommit = True
    checkpointer = SimpleEncryptedPostgresSaver(conn)
    checkpointer.setup()

    graph = build_graph().compile(checkpointer=checkpointer)
    snap0 = graph.get_state(config)

    state = None
    for i, patch in enumerate(patches, 1):

        state = graph.invoke(patch, config)
        print(f"\nINVOKE #{i}")
    
    if isinstance(state, RegistrationState):
        print("missing_fields:", state.missing_fields)
        print("validation_errors:", state.validation_errors)
    else:
        print("Graph ended. Current state:", state)

    hist = list(graph.get_state_history(config))
    print(f"\nCheckpoint count for thread_id={thread_id}: {len(hist)}")

    latest = graph.get_state(config)
    print("Latest snapshot keys:", list(latest.values.keys()))

if __name__ == "__main__":
    run_demo()