from flask import Flask, render_template, request, jsonify
import math
import sqlite3
import json
from datetime import datetime

app = Flask(__name__)

# --- Initialize SQLite Database ---
def init_db():
    conn = sqlite3.connect('reactor_history.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date_saved TEXT,
            material TEXT,
            volume_m3 REAL,
            capex_usd REAL,
            full_inputs TEXT,
            full_results TEXT
        )
    ''')
    conn.commit()
    conn.close()

init_db()

MATERIALS = {
    "ss304": {"density": 8000, "stress": 137.9},
    "ss316": {"density": 8000, "stress": 137.9},
    "carbon_steel": {"density": 7850, "stress": 118},
    "glass_lined": {"density": 7900, "stress": 110}
}

IMPELLERS = {
    'rushton': {'np': 5.0, 'ratio': 0.33},
    'pitched_blade': {'np': 1.3, 'ratio': 0.40},
    'anchor': {'np': 0.35, 'ratio': 0.90}
}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/calculate', methods=['POST'])
def calculate():
    data = request.json
    
    # 1. Inputs Parsing
    material = data.get('material', 'ss304')
    heating_type = data.get('heating_type', 'jacket')
    end_type = data.get('end_type', 'dish')
    diameter = float(data.get('diameter', 1.5))
    height = float(data.get('height', 2.5))
    pressure = float(data.get('pressure', 3.0))
    liquid_level = float(data.get('liquid_level', 1.5))
    
    reaction_rate = float(data.get('reaction_rate', 12.5))
    flow_rate = float(data.get('flow_rate', 1.0))
    conversion = float(data.get('conversion', 0.95))
    
    fluid_density = float(data.get('fluid_density', 1000.0))
    rpm = float(data.get('rpm', 120.0))
    impeller_type = data.get('impeller_type', 'pitched_blade')
    
    specific_heat = float(data.get('specific_heat', 4.18))
    temp_initial = float(data.get('temp_initial', 25.0))
    temp_target = float(data.get('temp_target', 85.0))
    batch_time = float(data.get('batch_time', 2.0))
    
    utility_type = data.get('utility_type', 'liquid')
    utility_cp = float(data.get('utility_cp', 4.18))
    utility_dt = float(data.get('utility_dt', 10.0))
    utility_latent = float(data.get('utility_latent', 2100.0))
    
    ambient_temp = float(data.get('ambient_temp', 25.0))
    insulation = data.get('insulation', 'insulated')
    
    utility_density = float(data.get('utility_density', 1000.0))
    utility_velocity = float(data.get('utility_velocity', 1.5))
    
    k_insulation = float(data.get('k_insulation', 0.04))
    safe_touch_temp = float(data.get('safe_touch_temp', 60.0))
    
    vapor_flow = float(data.get('vapor_flow', 50.0))
    vapor_latent = float(data.get('vapor_latent', 840.0))
    vapor_temp = float(data.get('vapor_temp', 78.0))
    cw_in = float(data.get('cw_in', 30.0))
    cw_out = float(data.get('cw_out', 40.0))
    u_cond = float(data.get('u_cond', 800.0))
    
    tube_od_mm = float(data.get('tube_od_mm', 19.05))
    tube_length_m = float(data.get('tube_length_m', 2.0))
    condenser_pressure = float(data.get('condenser_pressure', 1.0))
    condenser_material = data.get('condenser_material', 'carbon_steel')
    
    vapor_density = float(data.get('vapor_density', 2.5))
    condensate_density = float(data.get('condensate_density', 800.0))
    vapor_velocity = float(data.get('vapor_velocity', 20.0))
    liquid_velocity = float(data.get('liquid_velocity', 1.0))
    
    cost_per_kg = float(data.get('cost_per_kg', 12.0))
    cost_per_m2_condenser = float(data.get('cost_per_m2_condenser', 400.0))
    cost_per_kw_agitator = float(data.get('cost_per_kw_agitator', 600.0))
    installation_factor = float(data.get('installation_factor', 1.8))
    
    radius = diameter / 2.0
    pressure_mpa = pressure * 0.1
    
    # 2. Geometry
    if end_type == 'flat':
        v_end, a_end = 0, math.pi * (radius**2)
        h_head = 0.0
    elif end_type == 'hemispherical':
        v_end, a_end = (2/3) * math.pi * (radius**3), 2 * math.pi * (radius**2)
        h_head = radius
    elif end_type == 'conical':
        h_cone = radius * math.sqrt(3)
        v_end, a_end = (1/3) * math.pi * (radius**2) * h_cone, math.pi * radius * math.sqrt(radius**2 + h_cone**2)
        h_head = h_cone
    else: # dish
        v_end, a_end = 0.0847 * (diameter**3), 0.93 * (diameter**2)
        h_head = diameter * 0.2

    v_cylinder = math.pi * (radius**2) * height
    a_cylinder = math.pi * diameter * height
    total_volume = v_cylinder + (2 * v_end)
    total_metal_area = a_cylinder + (2 * a_end)
    jacket_ht_area = a_cylinder + a_end if heating_type != 'none' else 0
    partial_volume = v_end + (math.pi * (radius**2) * liquid_level)
    partial_ht_area = a_end + (math.pi * diameter * liquid_level) if heating_type != 'none' else 0

    # 3. Mechanical
    mat_props = MATERIALS.get(material, MATERIALS['ss304'])
    required_thickness = max(((pressure_mpa * (radius * 1000)) / mat_props["stress"]) + 3, 6)
    empty_weight = total_metal_area * (required_thickness / 1000.0) * mat_props["density"]

    # 4. Kinetic
    required_kinetic_vol = (flow_rate * conversion) / reaction_rate
    
    # 5. Thermal & Hydraulics
    htc = 800 if heating_type == 'limpet' else (500 if heating_type != 'none' else 0)
    surrounding_area = a_end + (jacket_ht_area * 1.15) if heating_type != 'none' else total_metal_area
    u_amb = 2.0 if insulation == 'insulated' else 15.0

    fluid_mass_kg = partial_volume * fluid_density
    time_seconds = batch_time * 3600
    sensible_duty_kw = (fluid_mass_kg * specific_heat * (temp_target - temp_initial)) / time_seconds if time_seconds > 0 else 0
    
    t_avg = (temp_initial + temp_target) / 2.0
    heat_loss_kw = (u_amb * surrounding_area * (t_avg - ambient_temp)) / 1000.0
    total_utility_duty_kw = sensible_duty_kw + heat_loss_kw
    abs_duty_kw = abs(total_utility_duty_kw)
    operation_mode = "Heating" if total_utility_duty_kw > 0 else "Cooling"

    if utility_type == 'steam':
        utility_flow_kg_s = abs_duty_kw / utility_latent if utility_latent > 0 else 0
    else:
        utility_flow_kg_s = abs_duty_kw / (utility_cp * utility_dt) if (utility_cp * utility_dt) > 0 else 0
        
    utility_flow_kg_hr = utility_flow_kg_s * 3600
    utility_vol_flow_m3_s = utility_flow_kg_s / utility_density if utility_density > 0 else 0
    pipe_area_m2 = utility_vol_flow_m3_s / utility_velocity if utility_velocity > 0 else 0
    pipe_id_mm = math.sqrt((4 * pipe_area_m2) / math.pi) * 1000 if pipe_area_m2 > 0 else 0

    h_air = 10.0
    insulation_thickness_mm = 0.0
    if insulation == 'insulated' and temp_target > safe_touch_temp and safe_touch_temp > ambient_temp:
        q_ambient = h_air * (safe_touch_temp - ambient_temp)
        insulation_thickness_mm = ((k_insulation * (temp_target - safe_touch_temp)) / q_ambient) * 1000

    # 6. Agitator & Baffles
    impeller = IMPELLERS.get(impeller_type, IMPELLERS['pitched_blade'])
    d_agitator = diameter * impeller['ratio']
    n_rps = rpm / 60.0
    
    power_watts = impeller['np'] * fluid_density * (n_rps**3) * (d_agitator**5)
    motor_kw = (power_watts / 1000.0) / 0.85
    motor_hp = motor_kw * 1.341

    torque_nm = power_watts / (2 * math.pi * n_rps) if n_rps > 0 else 0
    allowable_shear_stress_pa = (mat_props["stress"] * 1000000) * 0.5 
    shaft_diameter_mm = (((16 * torque_nm) / (math.pi * allowable_shear_stress_pa)) ** (1/3)) * 1000 if allowable_shear_stress_pa > 0 else 0
    design_shaft_diameter_mm = shaft_diameter_mm * 1.2 

    mounting_stool_m, clearance_m = 0.5, d_agitator
    shaft_length_m = mounting_stool_m + h_head + height + h_head - clearance_m
    if shaft_length_m <= 0: shaft_length_m = height

    num_baffles = 4
    baffle_width_mm = (diameter / 10.0) * 1000
    baffle_clearance_mm = baffle_width_mm / 6.0
    baffle_length_m = liquid_level 

    shaft_dia_m = design_shaft_diameter_mm / 1000.0
    moment_of_inertia = (math.pi * (shaft_dia_m ** 4)) / 64.0
    E_steel = 200e9
    stiffness_k = (3 * E_steel * moment_of_inertia) / (shaft_length_m ** 3) if shaft_length_m > 0 else 0
    
    equiv_mass_kg = (100 * (d_agitator ** 2)) + (0.24 * (math.pi * ((shaft_dia_m / 2) ** 2) * shaft_length_m * 7850))
    if equiv_mass_kg > 0 and stiffness_k > 0:
        critical_speed_rpm = math.sqrt(stiffness_k / equiv_mass_kg) * (60 / (2 * math.pi))
    else:
        critical_speed_rpm = 0
        
    if critical_speed_rpm == 0:
        vibration_status = "N/A"
    elif rpm < (0.8 * critical_speed_rpm):
        vibration_status = "Safe (Rigid Shaft Design)"
    elif rpm > (1.2 * critical_speed_rpm):
        vibration_status = "Safe (Flexible Shaft Design)"
    else:
        vibration_status = "WARNING: Dangerous Resonance Risk"

    # 7. Condenser
    cond_duty_kw = (vapor_flow / 3600.0) * vapor_latent
    cw_delta_t = cw_out - cw_in
    cw_flow_kg_hr = (cond_duty_kw * 3600.0) / (4.18 * cw_delta_t) if cw_delta_t > 0 else 0
    
    dt1, dt2 = vapor_temp - cw_out, vapor_temp - cw_in
    if dt1 <= 0 or dt2 <= 0:
        lmtd, cond_area_m2 = 0, 0
    elif dt1 == dt2:
        lmtd = dt1
        cond_area_m2 = (cond_duty_kw * 1000) / (u_cond * lmtd) if u_cond > 0 else 0
    else:
        lmtd = (dt1 - dt2) / math.log(dt1 / dt2)
        cond_area_m2 = (cond_duty_kw * 1000) / (u_cond * lmtd) if u_cond > 0 else 0

    if cond_area_m2 > 0 and tube_od_mm > 0 and tube_length_m > 0:
        single_tube_area = math.pi * (tube_od_mm / 1000.0) * tube_length_m
        num_tubes = math.ceil(cond_area_m2 / single_tube_area)
        bundle_diameter_mm = 1.05 * (1.25 * tube_od_mm) * math.sqrt(num_tubes)
        cond_shell_radius_mm = (bundle_diameter_mm + 20.0) / 2.0
        cond_mat_props = MATERIALS.get(condenser_material, MATERIALS['carbon_steel'])
        cond_required_thickness = max((((condenser_pressure * 0.1) * cond_shell_radius_mm) / cond_mat_props["stress"]) + 3, 6)
    else:
        num_tubes, bundle_diameter_mm, cond_shell_radius_mm, cond_required_thickness = 0, 0, 0, 0

    vapor_mass_flow_s = vapor_flow / 3600.0
    vapor_nozzle_mm = math.sqrt((4 * (vapor_mass_flow_s / vapor_density) / vapor_velocity) / math.pi) * 1000 if vapor_density > 0 and vapor_velocity > 0 else 0
    liquid_nozzle_mm = math.sqrt((4 * (vapor_mass_flow_s / condensate_density) / liquid_velocity) / math.pi) * 1000 if condensate_density > 0 and liquid_velocity > 0 else 0

    # 8. Economics
    reactor_body_cost = empty_weight * cost_per_kg
    agitator_cost = motor_kw * cost_per_kw_agitator
    condenser_cost = cond_area_m2 * cost_per_m2_condenser
    base_equipment_cost = reactor_body_cost + agitator_cost + condenser_cost
    total_installed_capex = base_equipment_cost * installation_factor

    results = {
        'geometry': {
            "total_volume": round(total_volume, 3),
            "partial_volume": round(partial_volume, 3),
            "jacket_ht_area": round(jacket_ht_area, 2),
            "partial_ht_area": round(partial_ht_area, 2)
        },
        'mechanical': {
            "required_thickness_mm": round(required_thickness, 2),
            "empty_weight_kg": round(empty_weight, 2),
            "material_selected": material
        },
        'kinetic': {
            "required_volume": round(required_kinetic_vol, 3),
            "volume_sufficient": "Yes" if total_volume >= required_kinetic_vol else "No (Increase Dimensions)"
        },
        'thermal': {
            "estimated_htc": htc,
            "surrounding_ht_area": round(surrounding_area, 2),
            "sensible_duty_kw": round(abs(sensible_duty_kw), 2),
            "heat_loss_kw": round(heat_loss_kw, 2),
            "total_duty_kw": round(abs_duty_kw, 2),
            "operation_mode": operation_mode,
            "utility_flow_kg_hr": round(utility_flow_kg_hr, 2),
            "utility_type": utility_type.capitalize(),
            "pipe_id_mm": round(pipe_id_mm, 2),
            "pipe_id_inches": round(pipe_id_mm / 25.4, 2),
            "insulation_thickness_mm": round(insulation_thickness_mm, 1)
        },
        'agitator': {
            "impeller_diameter_m": round(d_agitator, 2),
            "power_kw": round(motor_kw, 2),
            "power_hp": round(motor_hp, 2),
            "torque_nm": round(torque_nm, 2),
            "shaft_diameter_mm": round(design_shaft_diameter_mm, 2),
            "shaft_length_m": round(shaft_length_m, 2),
            "num_baffles": num_baffles,
            "baffle_width_mm": round(baffle_width_mm, 2),
            "baffle_clearance_mm": round(baffle_clearance_mm, 2),
            "baffle_length_m": round(baffle_length_m, 2),
            "critical_speed_rpm": round(critical_speed_rpm, 1),
            "vibration_status": vibration_status
        },
        'condenser': {
            "duty_kw": round(cond_duty_kw, 2),
            "cw_flow_kg_hr": round(cw_flow_kg_hr, 2),
            "lmtd": round(lmtd, 2),
            "area_m2": round(cond_area_m2, 2),
            "num_tubes": num_tubes,
            "bundle_diameter_mm": round(bundle_diameter_mm, 2),
            "shell_id_mm": round(cond_shell_radius_mm * 2, 2),
            "shell_thickness_mm": round(cond_required_thickness, 2),
            "shell_material": condenser_material.replace('_', ' ').title(),
            "vapor_nozzle_mm": round(vapor_nozzle_mm, 2),
            "liquid_nozzle_mm": round(liquid_nozzle_mm, 2)
        },
        'capex': {
            "reactor_body_cost": round(reactor_body_cost, 2),
            "agitator_cost": round(agitator_cost, 2),
            "condenser_cost": round(condenser_cost, 2),
            "base_equipment_cost": round(base_equipment_cost, 2),
            "total_installed_capex": round(total_installed_capex, 2),
            "installation_factor": installation_factor
        },
        'nozzles': data.get('nozzles', [])
    }

    try:
        conn = sqlite3.connect('reactor_history.db')
        c = conn.cursor()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        c.execute('''
            INSERT INTO history (date_saved, material, volume_m3, capex_usd, full_inputs, full_results)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            now, material, results['geometry']['total_volume'], 
            results['capex']['total_installed_capex'],
            json.dumps(data), json.dumps(results)
        ))
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Database Error: {e}")

    return jsonify(results)

@app.route('/history', methods=['GET'])
def get_history():
    conn = sqlite3.connect('reactor_history.db')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT id, date_saved, material, volume_m3, capex_usd, full_inputs FROM history ORDER BY id DESC LIMIT 20")
    rows = c.fetchall()
    conn.close()
    return jsonify([dict(ix) for ix in rows])

if __name__ == '__main__':
    app.run(debug=True, port=5000)