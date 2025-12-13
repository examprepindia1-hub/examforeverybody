import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np
import os

# 1. Setup Output Directory
output_dir = "sat_images"
if not os.path.exists(output_dir):
    os.makedirs(output_dir)

# Helper function to save images cleanly
def save_plot(filename, geometry_mode=False):
    if geometry_mode:
        plt.axis('equal')
        plt.axis('off')
    
    filepath = os.path.join(output_dir, filename)
    plt.savefig(filepath, bbox_inches='tight', dpi=300)
    plt.close()
    print(f"Generated: {filename}")

# ==========================================
# PART 1: DATA GRAPHS (Math Mod 1 & 2)
# ==========================================

def create_bar_graph():
    # Math Mod 1, Q1: Bar Graph Estimation
    activities = ['Debate', 'Robotics', 'Chess', 'Music']
    votes = [20, 35, 45, 15]
    
    plt.figure(figsize=(6, 4))
    plt.bar(activities, votes, color='#2c3e50')
    plt.title("Student Activity Votes")
    plt.ylabel("Number of Students")
    plt.grid(axis='y', linestyle='--', alpha=0.7)
    plt.yticks(np.arange(0, 51, 10))
    save_plot("math_m1_q1_bargraph.png")

def create_scatterplot():
    # Math Mod 1, Q10: Negative Slope
    np.random.seed(42)
    x = np.linspace(0, 10, 20)
    y = -2 * x + 20 + np.random.normal(0, 2, 20)
    
    plt.figure(figsize=(5, 5))
    plt.scatter(x, y, color='#e74c3c')
    plt.title("Variable Correlation")
    plt.xlabel("Variable x")
    plt.ylabel("Variable y")
    plt.grid(True, linestyle=':', alpha=0.6)
    save_plot("math_m1_q10_scatterplot.png")

def create_linear_graph():
    # Math Mod 1, Q12: Intercepts
    x = np.linspace(-2, 5, 10)
    y = 2 * x + 5
    
    plt.figure(figsize=(5, 5))
    plt.plot(x, y, linewidth=2, color='#2980b9', label='y = 2x + 5')
    plt.scatter([0, 2], [5, 9], color='black', zorder=5)
    plt.text(0.2, 5, "(0, 5)", fontsize=10)
    plt.text(2.2, 9, "(2, 9)", fontsize=10)
    
    plt.axhline(0, color='black', linewidth=1)
    plt.axvline(0, color='black', linewidth=1)
    plt.grid(True, linestyle='--')
    plt.title("Linear Function")
    save_plot("math_m1_q12_linegraph.png")

def create_population_graph():
    # Math Mod 2, Q1: Peak Value
    years = [2010, 2011, 2012, 2013, 2014, 2015, 2016]
    pop = [40, 42, 41, 44, 48, 50, 49] # in thousands
    
    plt.figure(figsize=(6, 4))
    plt.plot(years, pop, marker='o', linestyle='-', color='#27ae60')
    plt.title("City Population Over Time")
    plt.ylabel("Population (Thousands)")
    plt.xticks(years)
    plt.grid(True)
    save_plot("math_m2_q1_population.png")

def create_intersecting_lines():
    # Math Mod 2, Q16: Vertical Angles
    plt.figure(figsize=(5, 5))
    plt.plot([-5, 5], [-5, 5], color='black', linewidth=2)
    plt.plot([-5, 5], [5, -5], color='black', linewidth=2)
    
    plt.text(0, 1.5, r"$80^\circ$", horizontalalignment='center', fontsize=12)
    plt.text(0, -2.5, r"$2x^\circ$", horizontalalignment='center', fontsize=12)
    
    plt.xlim(-6, 6)
    plt.ylim(-6, 6)
    plt.axis('off')
    save_plot("math_m2_q16_geometry.png")

# ==========================================
# PART 2: GEOMETRY DIAGRAMS
# ==========================================

def create_circle_diagram():
    # Math Mod 1, Q20: Circle Arc
    fig, ax = plt.subplots(figsize=(4, 4))
    circle = patches.Circle((0, 0), 1, fill=False, edgecolor='black', linewidth=2)
    ax.add_patch(circle)
    
    x_b, y_b = np.cos(np.radians(60)), np.sin(np.radians(60))
    
    plt.plot([0, 1], [0, 0], color='black', marker='o') # OA
    plt.plot([0, x_b], [0, y_b], color='black', marker='o') # OB
    
    plt.text(-0.1, -0.1, "O", fontsize=12, weight='bold')
    plt.text(1.1, 0, "A", fontsize=12, weight='bold')
    plt.text(x_b + 0.1, y_b + 0.1, "B", fontsize=12, weight='bold')
    plt.text(0.5, 0.3, r"$60^\circ$", fontsize=10)
    
    plt.xlim(-1.2, 1.2)
    plt.ylim(-1.2, 1.2)
    save_plot("math_m1_q20_circle.png", geometry_mode=True)

def create_triangle_diagram():
    # Math Mod 1, Q22: Right Triangle
    fig, ax = plt.subplots(figsize=(4, 3))
    triangle = patches.Polygon([[0, 0], [4, 0], [0, 3]], closed=True, 
                               fill=None, edgecolor='black', linewidth=2)
    ax.add_patch(triangle)
    rect = patches.Rectangle((0, 0), 0.4, 0.4, fill=None, edgecolor='black')
    ax.add_patch(rect)
    
    plt.text(2, -0.4, "4", fontsize=12, ha='center')
    plt.text(-0.4, 1.5, "3", fontsize=12, va='center')
    plt.text(2.2, 1.6, "?", fontsize=12)
    
    plt.xlim(-1, 5)
    plt.ylim(-1, 4)
    save_plot("math_m1_q22_triangle.png", geometry_mode=True)

def create_cubes_diagram():
    # Math Mod 2, Q26: Surface Area of Cubes
    fig = plt.figure(figsize=(5, 3))
    ax = fig.add_subplot(111, projection='3d')
    
    def draw_cube(ax, origin):
        x, y, z = origin
        dx = [0, 1, 1, 0, 0]
        dy = [0, 0, 1, 1, 0]
        ax.plot([x+X for X in dx], [y+Y for Y in dy], [z]*5, 'k-')
        ax.plot([x+X for X in dx], [y+Y for Y in dy], [z+1]*5, 'k-')
        for i in range(4):
            ax.plot([x+dx[i], x+dx[i]], [y+dy[i], y+dy[i]], [z, z+1], 'k-')

    draw_cube(ax, (0, 0, 0))
    draw_cube(ax, (1, 0, 0))
    
    # Hide Axes for 3D plot requires specific command
    ax.set_axis_off()
    
    # Save manually here since 3D axes are tricky with generic savers
    plt.savefig(os.path.join(output_dir, "math_m2_q26_cubes.png"), bbox_inches='tight', dpi=300)
    plt.close()
    print(f"Generated: math_m2_q26_cubes.png")

# ==========================================
# EXECUTION
# ==========================================
if __name__ == "__main__":
    print(f"--- Generating 8 SAT Images in '{output_dir}/' ---")
    
    # Graphs
    create_bar_graph()
    create_scatterplot()
    create_linear_graph()
    create_population_graph()
    create_intersecting_lines()
    
    # Geometry
    create_circle_diagram()
    create_triangle_diagram()
    create_cubes_diagram()
    
    print("--- Success! Upload these to your Django Admin. ---")