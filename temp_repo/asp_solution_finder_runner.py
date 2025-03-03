# asp_solution_finder_runner.py
import subprocess
import os
from config.config import SPARC_JAR_PATH, ASP_FILE, OCCURS_OUTPUT


def update_n_in_file(asp_file, n):
    try:
        with open(asp_file, 'r', encoding='utf-8') as file:
            lines = file.readlines()

        with open(asp_file, 'w', encoding='utf-8') as file:
            for line in lines:
                if line.startswith("#const n ="):
                    file.write(f"#const n = {n}.\n")
                else:
                    file.write(line)
    except Exception as e:
        print(f"An error occurred: {e}")


def remove_generated_display_statements(asp_file):
    try:
        with open(asp_file, 'r', encoding='utf-8') as file:
            lines = file.readlines()

        with open(asp_file, 'w', encoding='utf-8') as file:
            for line in lines:
                if line.strip() == "% Automatically generated display statement" or line.startswith("display"):
                    continue
                file.write(line)

        remove_blank_lines_from_file(asp_file)
    except Exception as e:
        print(f"An error occurred: {e}")


def add_display_to_asp_file(asp_file, display_predicate):
    try:
        with open(asp_file, 'r', encoding='utf-8') as file:
            asp_code = file.read()

        asp_code = "\n".join([line for line in asp_code.splitlines() if not line.startswith("display")])

        asp_code += f"\n\n% Automatically generated display statement\n"
        asp_code += f"display {display_predicate}.\n"

        with open(asp_file, 'w', encoding='utf-8') as file:
            file.write(asp_code)
    except Exception as e:
        print(f"An error occurred: {e}")


def run_sparc_with_output_to_file(sparc_jar_path, asp_file, output_filename):
    command = f"java -jar {sparc_jar_path} {asp_file} -A > {output_filename}"
    process = subprocess.run(command, shell=True, stderr=subprocess.PIPE)

    if process.returncode != 0:
        print(f"Error running SPARC: {process.stderr.decode()}")
        raise Exception(f"SPARC failed with error: {process.stderr.decode()}")


def check_output_file(output_filename, required_content=""):
    try:
        if os.path.exists(output_filename):
            with open(output_filename, 'r', encoding='utf-8') as file:
                contents = file.read()
                if required_content:
                    return required_content in contents
                return bool(contents.strip())
        return False
    except Exception as e:
        print(f"An error occurred: {e}")
        return False


def print_file_contents(filename, predicate):
    try:
        if os.path.exists(filename):
            with open(filename, 'r', encoding='utf-8') as file:
                contents = file.read().strip()
                if contents:
                    print(f"\n----- {predicate.upper()} OUTPUT -----\n")
                    print(contents)
    except Exception as e:
        print(f"An error occurred: {e}")


def remove_blank_lines_from_file(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            lines = file.readlines()


        cleaned_lines = [line for line in lines if line.strip()]

        with open(file_path, 'w', encoding='utf-8') as file:
            file.writelines(cleaned_lines)
    except Exception as e:
        print(f"An error occurred while removing blank lines: {e}")
def get_minimal_n():
    sparc_jar_path = SPARC_JAR_PATH
    asp_file = ASP_FILE

    display_env = os.environ.get("DISPLAY_PREDICATES", "")
    if display_env.strip():
        display_predicates = display_env.split(",")
    else:
        display_predicates = ["occurs", "show_operated_holds_name", "show_changed_holds",
                              "show_changed_holds_name", "show_start_holds", "show_last_holds"]

    n = 1
    solution_found = False

    while not solution_found:
        print(f"Trying with n={n}")
        update_n_in_file(asp_file, n)
        occurs_output_filename = "occurs_output.txt"
        add_display_to_asp_file(asp_file, "occurs")
        run_sparc_with_output_to_file(sparc_jar_path, asp_file, occurs_output_filename)

        if check_output_file(occurs_output_filename, required_content="occurs"):
            solution_found = True
            print(f"Solution found with n={n}")

            break
        else:
            if os.path.exists(occurs_output_filename):
                os.remove(occurs_output_filename)
        remove_generated_display_statements(asp_file)
        n += 1

    return n


def main():
    sparc_jar_path = SPARC_JAR_PATH
    asp_file = ASP_FILE


    display_env = os.environ.get("DISPLAY_PREDICATES", "")
    if display_env.strip():
        display_predicates = display_env.split(",")
    else:

        display_predicates = ["occurs", "show_operated_holds_name", "show_changed_holds", "show_changed_holds_name",
                              "show_start_holds", "show_last_holds"]

    n = 1
    solution_found = False

    while not solution_found:
        print(f"Trying with n={n}")
        update_n_in_file(asp_file, n)

        occurs_output_filename = "occurs_output.txt"


        add_display_to_asp_file(asp_file, "occurs")
        run_sparc_with_output_to_file(sparc_jar_path, asp_file, occurs_output_filename)

        if check_output_file(occurs_output_filename, required_content="occurs"):
            solution_found = True
            print(f"Solution found with n={n}")
            print_file_contents(occurs_output_filename, "occurs")


            for predicate in display_predicates:
                if predicate == "occurs":
                    continue
                output_filename = f"{predicate}_output.txt"
                add_display_to_asp_file(asp_file, predicate)
                run_sparc_with_output_to_file(sparc_jar_path, asp_file, output_filename)
                print_file_contents(output_filename, predicate)
                remove_generated_display_statements(asp_file)
            break
        else:
            if os.path.exists(occurs_output_filename):
                os.remove(occurs_output_filename)

        remove_generated_display_statements(asp_file)
        n += 1

    print(f"The minimal value of n for the solution is: {n}")


if __name__ == "__main__":
    main()
