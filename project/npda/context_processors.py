def session_data(request):
    return {
        "can_complete_questionnaire": request.session.get(
            "can_complete_questionnaire", False
        ),
        "can_upload_csv": request.session.get("can_upload_csv", False),
        "pz_code": request.session.get("pz_code", None),
        # Add other session data as needed
    }
