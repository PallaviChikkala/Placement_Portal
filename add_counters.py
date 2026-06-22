import re

with open('templates/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace the values with data-target spans
content = re.sub(r'<div class="stat-value">([\d\.]+)\+</div>', r'<div class="stat-value"><span class="counter" data-target="\1">0</span>+</div>', content)
content = re.sub(r'<div class="stat-value">([\d\.]+)%</div>', r'<div class="stat-value"><span class="counter" data-target="\1">0</span>%</div>', content)
content = re.sub(r'<div class="stat-value">([\d\.]+)\s*<span style="font-size:1\.2rem;">LPA</span></div>', r'<div class="stat-value"><span class="counter" data-target="\1">0</span> <span style="font-size:1.2rem;">LPA</span></div>', content)

js_code = '''
function animateCounters(containerId) {
    const container = document.getElementById(containerId);
    if (!container) return;
    const counters = container.querySelectorAll('.counter');
    counters.forEach(counter => {
        counter.innerText = '0';
        const target = parseFloat(counter.getAttribute('data-target'));
        const isFloat = target % 1 !== 0;
        const duration = 1500;
        // avoid divide by zero
        if (target === 0) return;
        const increment = target / (duration / 16);
        let current = 0;
        const updateCounter = () => {
            current += increment;
            if (current < target) {
                counter.innerText = isFloat ? current.toFixed(2) : Math.ceil(current);
                requestAnimationFrame(updateCounter);
            } else {
                counter.innerText = target;
            }
        };
        updateCounter();
    });
}

function showStats(year) {
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.classList.remove('active');
        if (btn.innerText === year) btn.classList.add('active');
    });
    document.querySelectorAll('.stat-grid').forEach(grid => {
        grid.classList.remove('active');
    });
    document.getElementById('stats-' + year).classList.add('active');
    
    // animate
    animateCounters('stats-' + year);
}

// Initial animation when scrolling into view
document.addEventListener("DOMContentLoaded", () => {
    let section = document.querySelector('.stats-section');
    if (section) {
        let obs = new IntersectionObserver((entries) => {
            if(entries[0].isIntersecting) {
                animateCounters('stats-2025');
                obs.disconnect();
            }
        }, {threshold: 0.1});
        obs.observe(section);
    }
});
'''

# Replace the original showStats with our new one
content = re.sub(r'function showStats\(year\).*?\}', js_code, content, flags=re.DOTALL)

with open('templates/index.html', 'w', encoding='utf-8') as f:
    f.write(content)

print('Counters added successfully!')
