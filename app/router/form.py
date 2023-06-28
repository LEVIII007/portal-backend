from fastapi import APIRouter, HTTPException, Request
import requests
from settings import settings
from router import student, routes, enrollment_record
from request import build_request
import helpers
import mapping

router = APIRouter(prefix="/form-schema", tags=["Form"])

def build_returned_form_schema_data(
    returned_form_schema,
    total_number_of_fields,
    number_of_fields_left,
    form_attributes,
    priority,
):
    returned_form_schema[
        total_number_of_fields - number_of_fields_left
    ] = form_attributes[str(priority)]
    number_of_fields_left -= 1
    return returned_form_schema


@router.get("/")
def get_form_schema(form_schema_id: str):
    """
    This API returns a form schema when an ID is given

    Returns:
    list: form schema data if ID is a match, otherwise 404

    Example:
    > $BASE_URL/form_schema/?form_schema_id=1234
    returns [{form_schema_data_of_id_1234}]

    """
    response = requests.get(routes.form_db_url, params={"id": form_schema_id})
    if helpers.is_response_valid(response, "Form API could not fetch the data!"):
        return helpers.is_response_empty(response.json(), "Form does not exist")


@router.get("/student")
def get_student_fields(request: Request):
    query_params = helpers.validate_and_build_query_params(
        request, ["number_of_fields", "group", "student_id"]
    )

    # get the field ordering for a particular group
    form_group_mapping_response = requests.get(
        routes.form_db_url,
        params={"name": mapping.FORM_GROUP_MAPPING[query_params["group"]]},
    )

    if helpers.is_response_valid(
        form_group_mapping_response, "Could not fetch form-group mapping!"
    ):
        form = helpers.is_response_empty(
            form_group_mapping_response.json(),
            True,
            "Form-group mapping does not exist!",
        )[0]

        # get student and user data for the student ID that is requesting for profile completion
        # ASSUMPTION : student_id is valid and exists because only valid students will reach profile completion
        student_data = student.get_students(
            build_request(query_params={"student_id": query_params["student_id"]})
        )
        if student_data:

            student_data = student_data[0]

            # get enrollment data for the student
            enrollment_record_data = enrollment_record.get_enrollment_record(
                build_request(query_params={"student_id": student_data["user"]["id"]})
            )
            print(enrollment_record_data)
            # get the priorities for all fields and sort them
            priority_order = sorted([eval(i) for i in form["attributes"].keys()])

            # get the form attributes
            form_attributes = form["attributes"]

            # number of fields to sent back to the student
            total_number_of_fields = number_of_fields_left = int(
                query_params["number_of_fields"]
            )

            returned_form_schema = {}

            for priority in priority_order:

                if number_of_fields_left > 0:

                    # if the form field is first name of last name, we check if full name exists in the database
                    if (
                        form_attributes[str(priority)]["key"] == "first_name"
                        or form_attributes[str(priority)]["key"] == "last_name"
                    ):
                        if student_data["user"]["full_name"] is None:
                            build_returned_form_schema_data(
                                returned_form_schema,
                                total_number_of_fields,
                                number_of_fields_left,
                                form_attributes,
                                priority,
                            )

                    # if the form field is a user table attribute, we check in the user table
                    elif (
                        form_attributes[str(priority)]["key"]
                        in mapping.USER_QUERY_PARAMS
                    ):

                        if (
                            student_data["user"][form_attributes[str(priority)]["key"]]
                            is None
                        ):

                            build_returned_form_schema_data(
                                returned_form_schema,
                                total_number_of_fields,
                                number_of_fields_left,
                                form_attributes,
                                priority,
                            )

                        # if the form field is a enrollment record table attribute, we check in the enrollement record table
                    elif (
                            form_attributes[str(priority)]["key"]
                            in mapping.ENROLLMENT_RECORD_PARAMS and form_attributes[str(priority)]["key"] != "student_id"
                        ):

                            if (form_attributes[str(priority)]["key"]== "school_name"):

                                print(enrollment_record_data)
                                if enrollment_record_data == [] or enrollment_record_data[0]["school_id"] is None:
                                    if enrollment_record_data == [] or student_data["user"]["district"] is None:
                                        if enrollment_record_data == []  or student_data["user"]["state"] is None:
                                            returned_form_schema[total_number_of_fields - number_of_fields_left] = [x for x in list(form_attributes.values())if x["key"] == "state"][0]
                                            number_of_fields_left -= 1
                                        else:
                                            returned_form_schema[
                                                total_number_of_fields
                                                - number_of_fields_left
                                            ] = [
                                                x
                                                for x in list(form_attributes.values())
                                                if x["key"] == "district"
                                            ][
                                                0
                                            ]
                                            number_of_fields_left -= 1
                                    else:
                                        returned_form_schema[
                                            total_number_of_fields
                                            - number_of_fields_left
                                        ] = [
                                            x
                                            for x in list(form_attributes.values())
                                            if x["key"] == "school_name"
                                        ][
                                            0
                                        ]
                                        number_of_fields_left -= 1
                            else:
                                if (enrollment_record_data == [] or enrollment_record_data[0][form_attributes[str(priority)]["key"]]is None):
                                    build_returned_form_schema_data(
                                            returned_form_schema,
                                            total_number_of_fields,
                                            number_of_fields_left,
                                            form_attributes,
                                            priority,
                                        )

                    else:
                        if student_data[form_attributes[str(priority)]["key"]] is None:
                            build_returned_form_schema_data(
                                returned_form_schema,
                                total_number_of_fields,
                                number_of_fields_left,
                                form_attributes,
                                priority,
                            )

            return returned_form_schema
        else:
            raise HTTPException(status_code=404, detail="Student does not exist!")
