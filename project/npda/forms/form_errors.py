# Errors are saved as a top level field when uploading a CSV
# When filling out the questionnaire they are on each field in the form
# Even though you only ever have one or the other, we want to render them
# in the same way so make unified accessors
def lookup_errors(form, instance, field_name):
    if field_name in form.errors:
        return form.errors[field_name]
    
    if instance.errors and field_name in instance.errors:
        return [error["message"] for error in instance.errors[field_name]]
    
    return []
