import re
# path/filename: /mnt/data/md_parser_updated.py
def extract_steps_and_code(md_content):
    """
    Improved parsing function to accurately extract descriptions and code examples from markdown content.
    """
    parsed_content = {
        "instructions": "",
        "steps": []
    }

    # Extract instructions
    instructions_match = re.search(r'# Title of the document\n(.+?)(?=\n# )', md_content, re.DOTALL)
    if instructions_match:
        parsed_content["instructions"] = instructions_match.group(1).strip()

    # Extract steps with improved regex for descriptions and code examples
    step_pattern = r'### Step (\d+): (.*?)\n#### Description of the step\n(.*?)(?=\n### Step |\n#### Example:|\n$)'
    steps = re.findall(step_pattern, md_content, re.DOTALL)

    for step in steps:
        step_number, step_name, step_description = step
        step_dict = {
            "number": step_number.strip(),
            "name": step_name.strip(),
            "description": step_description.strip(),
            "code_examples": []
        }

        # Extract code examples
        example_pattern = r'#### Example: (.*?)\n```(.*?)```'
        examples = re.findall(example_pattern, md_content[md_content.find(step_description):], re.DOTALL)
        
        for example in examples:
            example_title, example_code = example
            example_dict = {
                "description": example_title.strip(),
                "code": example_code.strip()
            }
            step_dict["code_examples"].append(example_dict)

        parsed_content["steps"].append(step_dict)

    return parsed_content

def get_step_by_index(steps_data, index):
    return steps_data.get(index, "Step not found.")

# Note: The next steps involve testing this updated function with the markdown content.

# Execute the adjusted function to extract steps with direct indexing and associated code examples,
# along with other information in a secondary output.

# Display the first few steps with their titles and associated code for verification


# Re-extract elements with the adjusted function to correctly handle code comments
with open('/home/crochetch/Documents/Projects/VerificationQUIC/PFV/src/llm/neoivy/_system_prompt/knowledge/NewProject.md', 'r') as f:
    content = f.read()
steps_with_code = extract_steps_and_code(content)



# Example usage: Access step 1 details
step_1_details = get_step_by_index(steps_with_code, 1)
#print(step_1_details)

# print(steps_with_code)

# Check the structure of the first few sections for verification
print(steps_with_code.keys())
for key, element in steps_with_code.items():
    print("------------------------------")
    print(key)
    if key == "instructions":
        print(element)
    if key == "steps":
        for item in element:
            print("Step " + item["number"] + ": " + item["name"])
            print("Description: " + item["description"])
            for subitem in item["code_examples"]:
                print("Code Example: " + subitem["description"])
                print(subitem["code"][0])
                print(subitem["code"][-1])
                #print(element[item][subitem])
            # print("------------------------------")
            exit()
        # exit()
    print("------------------------------")
    
# for element in other_info.items():
#     print(element)
#     print("------------------------------")
    
    