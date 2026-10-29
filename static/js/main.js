// Tab Switching
function openTab(evt, tabName) {
    let i, tabcontent, tablinks;
    tabcontent = document.getElementsByClassName("tabcontent");
    for (i = 0; i < tabcontent.length; i++) {
        tabcontent[i].style.display = "none";
    }
    tablinks = document.getElementsByClassName("tablinks");
    for (i = 0; i < tablinks.length; i++) {
        tablinks[i].className = tablinks[i].className.replace(" active", "");
    }
    document.getElementById(tabName).style.display = "block";
    if(evt) {
        evt.currentTarget.className += " active";
    }
}

// Form Submission
document.getElementById('calculatorForm').addEventListener('submit', function(e) {
    e.preventDefault();
    
    document.getElementById('resultsTabBtn').className += " active";
    document.querySelector('.tablinks').className = "tablinks"; 
    openTab(null, 'Results');
    document.getElementById('resultsTabBtn').className += " active";

    document.getElementById('loading').style.display = 'block';
    document.getElementById('resultsContent').style.display = 'none';
    document.getElementById('downloadPdfBtn').style.display = 'none';

    const formData = new FormData(this);
    const data = Object.fromEntries(formData.entries());
    data.nozzles = formData.getAll('nozzles'); 

    fetch('/calculate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
    })
    .then(response => response.json())
    .then(result => {
        document.getElementById('loading').style.display = 'none';
        document.getElementById('resultsContent').style.display = 'block';
        document.getElementById('downloadPdfBtn').style.display = 'block';
        
        let html = `
            <div class="result-section">
                <h4>Mechanical & Volumetric Design</h4>
                <p>Material: <strong>${result.mechanical.material_selected.toUpperCase()}</strong></p>
                <p>Total Internal Volume: <strong>${result.geometry.total_volume} m³</strong></p>
                <p>Working Volume at Partial Level: <strong>${result.geometry.partial_volume} m³</strong></p>
                <p>Calculated Shell Thickness: <strong>${result.mechanical.required_thickness_mm} mm</strong></p>
                <p>Empty Reactor Weight: <strong>${result.mechanical.empty_weight_kg} kg</strong></p>
            </div>

            <div class="result-section">
                <h4>Kinetic Assessment</h4>
                <p>Required Reaction Volume: <strong>${result.kinetic.required_volume} m³</strong></p>
                <p>Volume Capacity Check: <strong>${result.kinetic.volume_sufficient}</strong></p>
            </div>

            <div class="result-section">
                <h4>Thermal & Heating/Cooling Setup</h4>
                <p>Primary Mode: <strong>${result.thermal.operation_mode}</strong></p>
                <p>Sensible Fluid Duty: <strong>${result.thermal.sensible_duty_kw} kW</strong></p>
                <p>Environmental Heat Transfer (Loss/Gain): <strong>${result.thermal.heat_loss_kw} kW</strong></p>
                <p style="color: #0056b3; font-weight: bold; border-top: 1px solid #ccc; padding-top: 5px;">
                    Total Compensated Duty: ${result.thermal.total_duty_kw} kW
                </p>
                <p>Required Utility Mass Flow (${result.thermal.utility_type}): <strong>${result.thermal.utility_flow_kg_hr} kg/hr</strong></p>
                <p>Required Utility Pipe ID: <strong>${result.thermal.pipe_id_mm} mm (${result.thermal.pipe_id_inches} inches)</strong></p>
                <p>Required Insulation Thickness: <strong>${result.thermal.insulation_thickness_mm > 0 ? result.thermal.insulation_thickness_mm + ' mm' : 'N/A (Temp is safe)'}</strong></p>
            </div>

            <div class="result-section">
                <h4>Agitator & Internals Design</h4>
                <p>Calculated Impeller Diameter: <strong>${result.agitator.impeller_diameter_m} m</strong></p>
                <p>Required Motor Power: <strong>${result.agitator.power_kw} kW (${result.agitator.power_hp} HP)</strong></p>
                <p>Minimum Shaft Diameter: <strong>${result.agitator.shaft_diameter_mm} mm</strong></p>
                <p>Estimated Shaft Length: <strong>${result.agitator.shaft_length_m} m</strong></p>
                
                <p style="color: #0056b3; font-weight: bold; border-top: 1px solid #ccc; padding-top: 5px; margin-top: 10px;">Anti-Swirl Baffles</p>
                <p>Quantity: <strong>${result.agitator.num_baffles} (Spaced 90° apart)</strong></p>
                <p>Baffle Width: <strong>${result.agitator.baffle_width_mm} mm</strong></p>
                
                <p style="color: #0056b3; font-weight: bold; border-top: 1px solid #ccc; padding-top: 5px; margin-top: 10px;">Vibration Analysis</p>
                <p>1st Critical Speed (Nc): <strong>${result.agitator.critical_speed_rpm} RPM</strong></p>
                <p>Safety Check: <strong style="color: ${result.agitator.vibration_status.includes('WARNING') ? '#dc3545' : '#28a745'};">${result.agitator.vibration_status}</strong></p>
            </div>

            <div class="result-section">
                <h4>Reflux Condenser Design</h4>
                <p>Condenser Heat Duty: <strong>${result.condenser.duty_kw} kW</strong></p>
                <p>Required Cooling Water Flow: <strong>${result.condenser.cw_flow_kg_hr} kg/hr</strong></p>
                <p>Required Heat Transfer Area: <strong>${result.condenser.area_m2} m²</strong></p>
                
                <p style="color: #0056b3; font-weight: bold; border-top: 1px solid #ccc; padding-top: 5px; margin-top: 10px;">Tube Layout & Shell</p>
                <p>Total Number of Tubes: <strong>${result.condenser.num_tubes}</strong></p>
                <p>Estimated Bundle Diameter: <strong>${result.condenser.bundle_diameter_mm} mm</strong></p>
                <p>Shell Inner Diameter: <strong>${result.condenser.shell_id_mm} mm</strong></p>
                <p>Required Shell Thickness: <strong>${result.condenser.shell_thickness_mm} mm</strong></p>
                
                <p style="color: #0056b3; font-weight: bold; border-top: 1px solid #ccc; padding-top: 5px; margin-top: 10px;">Nozzles</p>
                <p>Vapor Inlet ID: <strong>${result.condenser.vapor_nozzle_mm} mm</strong></p>
                <p>Liquid Outlet ID: <strong>${result.condenser.liquid_nozzle_mm} mm</strong></p>
            </div>
            
            <div class="result-section">
                <h4>Required Reactor Nozzles</h4>
                <ul>
                    ${result.nozzles.length > 0 ? result.nozzles.map(n => `<li>${n}</li>`).join('') : '<li>None selected</li>'}
                </ul>
            </div>

            <div class="result-section">
                <h4>Economic Estimation (CAPEX)</h4>
                <div style="display: flex; flex-wrap: wrap; gap: 20px;">
                    <div style="flex: 1; min-width: 250px;">
                        <p>Reactor Body: <strong>$${result.capex.reactor_body_cost.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}</strong></p>
                        <p>Agitator System: <strong>$${result.capex.agitator_cost.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}</strong></p>
                        <p>Condenser: <strong>$${result.capex.condenser_cost.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}</strong></p>
                        <p>Bare Equipment: <strong>$${result.capex.base_equipment_cost.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}</strong></p>
                        <p style="color: #28a745; font-size: 1.1em; font-weight: bold; border-top: 1px solid #ccc; padding-top: 10px; margin-top: 10px;">
                            Total Installed CAPEX: $${result.capex.total_installed_capex.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}
                        </p>
                    </div>
                    <div style="flex: 1; min-width: 250px; display: flex; justify-content: center; align-items: center; max-height: 250px;">
                        <canvas id="capexChart"></canvas>
                    </div>
                </div>
            </div>
        `;
        
        document.getElementById('resultsContent').innerHTML = html;

        // Render Chart
        if (window.capexChartInstance) {
            window.capexChartInstance.destroy();
        }
        const ctx = document.getElementById('capexChart').getContext('2d');
        window.capexChartInstance = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: ['Reactor Body', 'Agitator', 'Condenser'],
                datasets: [{
                    data: [result.capex.reactor_body_cost, result.capex.agitator_cost, result.capex.condenser_cost],
                    backgroundColor: ['#007bff', '#28a745', '#ffc107']
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { position: 'bottom' } }
            }
        });
    })
    .catch(error => {
        console.error('Error:', error);
        document.getElementById('loading').style.display = 'none';
        document.getElementById('resultsContent').innerHTML = '<p style="color:red;">Error calculating data.</p>';
        document.getElementById('resultsContent').style.display = 'block';
    });
});

// PDF Generation
document.getElementById('downloadPdfBtn').addEventListener('click', function() {
    const element = document.getElementById('resultsContent');
    const opt = {
        margin: [0.5, 0.5, 0.5, 0.5],
        filename: 'Reactor_Design_Report.pdf',
        image: { type: 'jpeg', quality: 0.98 },
        html2canvas: { scale: 2 },
        jsPDF: { unit: 'in', format: 'letter', orientation: 'portrait' }
    };
    html2pdf().set(opt).from(element).save();
});

// History Logic
window.historyData = {};

window.loadHistory = function() {
    const tbody = document.getElementById('historyTableBody');
    tbody.innerHTML = '<tr><td colspan="5" style="padding: 10px; text-align: center;">Loading...</td></tr>';
    
    fetch('/history')
    .then(response => response.json())
    .then(data => {
        tbody.innerHTML = '';
        window.historyData = {}; 
        
        if (data.length === 0) {
            tbody.innerHTML = '<tr><td colspan="5" style="padding: 10px; text-align: center;">No saved designs found.</td></tr>';
            return;
        }
        
        data.forEach(row => {
            window.historyData[row.id] = JSON.parse(row.full_inputs);
            tbody.innerHTML += `
                <tr style="border-bottom: 1px solid #eee;">
                    <td style="padding: 10px;">${row.date_saved}</td>
                    <td style="padding: 10px; text-transform: uppercase;">${row.material.replace('_', ' ')}</td>
                    <td style="padding: 10px;">${row.volume_m3.toFixed(2)}</td>
                    <td style="padding: 10px;">$${row.capex_usd.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}</td>
                    <td style="padding: 10px;">
                        <button type="button" onclick="reloadDesign(${row.id})" style="padding: 5px 10px; background-color: #007bff; color: white; border: none; border-radius: 4px; cursor: pointer;">
                            ↺ Reload
                        </button>
                    </td>
                </tr>
            `;
        });
    })
    .catch(err => {
        tbody.innerHTML = '<tr><td colspan="5" style="padding: 10px; text-align: center; color: red;">Error loading history.</td></tr>';
    });
};

window.reloadDesign = function(id) {
    const savedInputs = window.historyData[id];
    if (!savedInputs) return;
    const form = document.getElementById('calculatorForm');
    
    for (const key in savedInputs) {
        if (key === 'nozzles') {
            form.querySelectorAll('input[name="nozzles"]').forEach(cb => cb.checked = false);
            savedInputs[key].forEach(val => {
                const cb = form.querySelector(`input[name="nozzles"][value="${val}"]`);
                if (cb) cb.checked = true;
            });
        } else {
            const field = form.querySelector(`[name="${key}"]`);
            if (field) field.value = savedInputs[key];
        }
    }
    
    const tabs = document.getElementsByClassName("tablinks");
    for (let i = 0; i < tabs.length; i++) {
        tabs[i].className = tabs[i].className.replace(" active", "");
    }
    tabs[0].className += " active"; 
    openTab(null, 'InputParams'); 
    window.scrollTo(0,0);
};