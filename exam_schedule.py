import csv
from csp import CSP, backtracking_search, forward_checking, mac, min_conflicts, mrv, dom_wdeg
import time
from tabulate import tabulate

total_days = 22  #Total days of exams + 1 (for 21 days of exam, let it 22, for 16 days insert 17 etc)

def read_courses(file_path): #reads the data from the CSV
    courses = []
    with open(file_path, encoding='ISO-8859-7') as file:  #for greek language encoding, failed with utf-8 encoding
        reader = csv.DictReader(file)
        for row in reader:
            courses.append(row)
    return courses

def create_exam_csp(courses):
    variables = []
    domains = {}
    neighbors = {}
    weights = {}

    
    for course in courses: #step 1: create variables and domains
        course_name = course["Μάθημα"]  #course name
        variables.append(course_name)

        
        domains[course_name] = [(day, slot) for day in range(1, total_days) for slot in range(1, 4)] #the domain for each course is all combinations of 21 days * 3 time slots

        
        if course["Εργαστήριο (TRUE/FALSE)"] == "TRUE":  #if the course has a lab, add a separate variable for the lab
            lab_name = f"{course_name} (Εργαστήριο)"  #name for the lab exam
            variables.append(lab_name)
            domains[lab_name] = [(day, slot) for day in range(1, total_days) for slot in range(1, 4)]
    
    for var in variables: #step 2: define neighbors
        neighbors[var] = set(variables) - {var}

    def constraints(A, a, B, b): #step 3: define constraints function
        csp.constraint_check_count += 1  #counter for each constraint check
        
        if A.endswith("(Εργαστήριο)") and B == A.replace(" (Εργαστήριο)", ""): #constraint for lab exams following theory exams (next slot of the same day)
            return a[0] == b[0] and a[1] == b[1] + 1  #same day and the lab has to be next slot
        if B.endswith("(Εργαστήριο)") and A == B.replace(" (Εργαστήριο)", ""):
            return b[0] == a[0] and b[1] == a[1] + 1  #same day and the lab has to be next slot

        instructor_A = next((c["Καθηγητής"] for c in courses if c["Μάθημα"] == A), None)  #same professor constraint
        instructor_B = next((c["Καθηγητής"] for c in courses if c["Μάθημα"] == B), None)
        if instructor_A == instructor_B and instructor_A is not None:
            return a[0] != b[0]  #Cannot be on the same day

        #difficult lessons constraint (at least 2 days apart)
        if any(A == course["Μάθημα"] and course["Δύσκολο (TRUE/FALSE)"] == "TRUE" for course in courses) and \
           any(B == course["Μάθημα"] and course["Δύσκολο (TRUE/FALSE)"] == "TRUE" for course in courses):
            return abs(a[0] - b[0]) >= 2  #ensure at least 2 days apart for difficult courses

        semester_A = next((c["Εξάμηνο"] for c in courses if c["Μάθημα"] == A), None)   #same semester constraint (cannot be on the same day)
        semester_B = next((c["Εξάμηνο"] for c in courses if c["Μάθημα"] == B), None)
        if semester_A == semester_B and semester_A is not None:
            return a[0] != b[0]  #cannot be on the same day

        if a == b:  #ensure exams are scheduled in different slots on the same day for different courses
            return False  #cannot schedule in the same slot on the same day two exams

        
        return True #if no specific constraints are violated,send true

    
    return CSP(variables, domains, neighbors, constraints, weights) #step 4: return the CSP object

def print_solution(solution, csp):
    if solution is None:
        print("No solution found.")
        return
    
    schedule = {} #create a dictionary to group courses by day
    for var, value in solution.items():
        day, slot = value
        if day not in schedule:
            schedule[day] = []
        schedule[day].append((var, slot))

    
    for day in range(1, total_days):  #Print the slots per day from the first to the last day
        if day in schedule:
            print(f"Day {day}:")
            for slot in range(1, 4):  #3 slots per day
                print(f"  Slot {slot}: ", end="")
                exams = [var for var, s in schedule[day] if s == slot]
                if exams:
                    print(", ".join(exams))
                else:
                    print("No exam")
            print("-" * 50)

#Solve and measure time
def solve_csp(csp, inference=None, select_unassigned_variable=None):
    start_time = time.time()    #we have calculating time here and we have some getters needed for the metrics
    solution = backtracking_search(csp, inference=inference, select_unassigned_variable=select_unassigned_variable)
    end_time = time.time()
    elapsed_time = end_time - start_time
    constraint_checks = csp.constraint_check_count
    total_assignments = csp.nassigns
    
    return solution, elapsed_time, constraint_checks, total_assignments

#Main function
if __name__ == "__main__":
    courses = read_courses("h3-data.csv") #get data from csv
    csp = create_exam_csp(courses) #create the CSP problem
    results = [] #store the results for comparisons after the execution
    
    configurations = [  #different configurations for the backtrack search function as we need later for comparison
        ("FC + MRV", forward_checking, mrv),  #fc w/ MRV 
        ("MAC + MRV", mac, mrv),  #MAC w/ MRV
        ("FC + DOM/WDEG", forward_checking, dom_wdeg),  #fc w/ DOM/WDEG
        ("MAC + DOM/WDEG", mac, dom_wdeg),  #MAC w/ DOM/WDEG
    ]

    for config_name, inference, select_unassigned_variable in configurations:
        print(f"Configuration: {config_name}")
        solution, elapsed_time, constraint_checks, total_assignments = solve_csp(csp, inference=inference, select_unassigned_variable=select_unassigned_variable)
        print_solution(solution, csp)
        results.append([config_name, elapsed_time, constraint_checks, total_assignments])
        csp.constraint_check_count = 0  #Rreset the two counters for the metrics since we need them zero'ed for the next configuration
        csp.nassigns = 0 

    
    print("Configuration: Min Conflicts") #min Conflicts configuration separately because it doesnt run with backtrack search
    start_time = time.time()
    solution = min_conflicts(csp)
    end_time = time.time()
    elapsed_time = end_time - start_time
    print_solution(solution, csp)
    results.append(["Min Conflicts", elapsed_time, csp.constraint_check_count, csp.nassigns])

    
    print("\nComparison of Metrics:") #print the results in a beautiful table format for better understanding of the metrics
    headers = ["Configuration", "Time (s)", "Constraint Checks", "Assignments"]
    print(tabulate(results, headers=headers, tablefmt="grid"))