

class TestStatusUtility:

    def test_case_try_except_pass(test_case_id, response_data):
        return{
            "test_case_id": test_case_id,"status": "Passed",
                "response_data": response_data}
    
    def test_case_try_except_fail(test_case_id, response_data, e ):
        return{
                "test_case_id": test_case_id,"status": "Failed",
                "response_data": f"{response_data}",
                "error": f"Test case {test_case_id} failed. Validation failed: {e}"}
    
    def test_case_not_equal_200_status(test_case_id, response_data):

        return{
                "test_case_id": test_case_id,
                "status": "Failed",
                "error": f"Status code: {response_data.status_code} - {response_data.text} "
        }