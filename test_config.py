#### ~~~~ Don’t import any other file here or don’t create any other new function & Class here ~~~~ ####
# from dotenv import load_dotenv


def get_var_by_environment(input_env):

    #### test case file path ###
    test_run_config = {

        "new_test_case_file" : "/Users/karthick/Documents/pythonBasicProject/carrier_integration_v2/fb-rpa-e2e/excel_files/",

        "global_api_user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
    }
    
    if input_env.lower() == "dev":
        dev_vars =  {
            "environment": "dev",
            "vendor_id": "",
            "api_base_url": "",
            "efp_api_base_url": "",
            "referer_domain": "",
            "access_token": ""
        }
        test_run_config.update(dev_vars)
        return test_run_config
    
    elif input_env.lower() == "qa":
        qa_vars = {
            "environment": "qa",
            "vendor_id": "",
            "api_base_url": "",
            "efp_api_base_url": "",
            "referer_domain": "",
            "access_token": "",
            "ais_api_base_url": "",
            "ais_jerry_api_base_url": ""
        }
        test_run_config.update(qa_vars)
        return test_run_config
    
    elif input_env.lower() == "staging":
        stag_vars = {
            "environment": "", 
            "vendor_id": "",
            "api_base_url": "", 
            "efp_api_base_url": "", 
            "referer_domain": "", 
            "access_token": "",
            "admin_portal_api_base_url": "",
            "admin_portal_access_token": "",
        }
        test_run_config.update(stag_vars)
        return test_run_config
    
    elif input_env.lower()== "prod":
        prod_vars = {
            ## Production ###
            "environment": "prod",
            "vendor_id": "",
            "api_base_url": "", 
            "referer_domain": "",
            "access_token": "",
            "admin_portal_api_base_url": "",
            "admin_portal_access_token": ""
            }
        test_run_config.update(prod_vars)
        return test_run_config
    
    else: 
        test_run_config = []
        raise ValueError("Invalid environment specified. Please use 'dev', 'qa', 'staging', or 'prod'.")


# env = test_run_environment = os.getenv("CURRECNT_TEST_RUN_ENV")

# test_run_config = get_var_by_environment(env)