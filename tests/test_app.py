from copy import deepcopy

import pytest
from fastapi.testclient import TestClient

from src import app as app_module


client = TestClient(app_module.app)


@pytest.fixture(autouse=True)
def restore_activities():
    original_activities = deepcopy(app_module.activities)
    yield
    app_module.activities.clear()
    app_module.activities.update(original_activities)


def test_root_redirects_to_static_index():
    # Arrange
    expected_location = "/static/index.html"

    # Act
    response = client.get("/", follow_redirects=False)

    # Assert
    assert response.status_code == 307
    assert response.headers["location"] == expected_location


def test_get_activities_returns_activity_details():
    # Arrange
    expected_fields = {"description", "schedule", "max_participants", "participants"}

    # Act
    response = client.get("/activities")

    # Assert
    assert response.status_code == 200
    activities = response.json()
    assert "Chess Club" in activities
    assert expected_fields <= activities["Chess Club"].keys()
    assert isinstance(activities["Chess Club"]["participants"], list)


def test_signup_adds_new_participant():
    # Arrange
    activity = "Drama Club"
    email = "new-student@mergington.edu"

    # Act
    response = client.post(f"/activities/{activity}/signup", params={"email": email})

    # Assert
    assert response.status_code == 200
    assert response.json() == {"message": f"Signed up {email} for {activity}"}
    assert email in app_module.activities[activity]["participants"]


def test_duplicate_signup_returns_error_without_duplicate():
    # Arrange
    activity = "Chess Club"
    email = "michael@mergington.edu"
    original_count = app_module.activities[activity]["participants"].count(email)

    # Act
    response = client.post(f"/activities/{activity}/signup", params={"email": email})

    # Assert
    assert response.status_code == 400
    assert response.json()["detail"] == "Student already signed up for this activity"
    assert app_module.activities[activity]["participants"].count(email) == original_count


def test_signup_for_unknown_activity_returns_error():
    # Arrange
    activity = "Unknown Activity"
    email = "student@mergington.edu"

    # Act
    response = client.post(f"/activities/{activity}/signup", params={"email": email})

    # Assert
    assert response.status_code == 404
    assert response.json()["detail"] == "Activity not found"


def test_unregister_removes_existing_participant():
    # Arrange
    activity = "Soccer Team"
    email = "student@mergington.edu"
    app_module.activities[activity]["participants"].append(email)

    # Act
    response = client.delete(f"/activities/{activity}/signup", params={"email": email})

    # Assert
    assert response.status_code == 200
    assert response.json() == {"message": f"Unregistered {email} from {activity}"}
    assert email not in app_module.activities[activity]["participants"]


def test_unregister_missing_participant_returns_error():
    # Arrange
    activity = "Soccer Team"
    email = "not-registered@mergington.edu"

    # Act
    response = client.delete(f"/activities/{activity}/signup", params={"email": email})

    # Assert
    assert response.status_code == 404
    assert response.json()["detail"] == "Student is not signed up for this activity"


def test_unregister_from_unknown_activity_returns_error():
    # Arrange
    activity = "Unknown Activity"
    email = "student@mergington.edu"

    # Act
    response = client.delete(f"/activities/{activity}/signup", params={"email": email})

    # Assert
    assert response.status_code == 404
    assert response.json()["detail"] == "Activity not found"


@pytest.mark.parametrize("method, path", [("post", "/activities/Drama Club/signup"), ("delete", "/activities/Drama Club/signup")])
def test_missing_email_returns_validation_error(method, path):
    # Arrange
    request = getattr(client, method)

    # Act
    response = request(path)

    # Assert
    assert response.status_code == 422


def test_valid_email_format_is_accepted():
    # Arrange
    activity = "Drama Club"
    email = "valid.student+club@mergington.edu"

    # Act
    response = client.post(f"/activities/{activity}/signup", params={"email": email})

    # Assert
    assert response.status_code == 200
    assert email in app_module.activities[activity]["participants"]


@pytest.mark.xfail(reason="Email format validation is not implemented yet", strict=False)
@pytest.mark.parametrize("email", ["not-an-email", "missing-at.example.com", "@missing-local.com"])
def test_invalid_email_format_is_rejected(email):
    # Arrange
    activity = "Drama Club"

    # Act
    response = client.post(f"/activities/{activity}/signup", params={"email": email})

    # Assert
    assert response.status_code == 422
