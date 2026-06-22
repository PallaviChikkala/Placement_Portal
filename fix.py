import os
for r, d, files in os.walk('templates'):
    for f in files:
        if f.endswith('.html'):
            p = os.path.join(r, f)
            with open(p, 'r', encoding='utf-8') as f_in:
                c = f_in.read()
            c = c.replace('rgba(255, 255, 255, 0.4)', 'rgba(255, 255, 255, 0.1)')
            if 'document.body.appendChild(m)' not in c:
                c = c.replace('</body>', '<script>document.addEventListener("DOMContentLoaded", function() { document.querySelectorAll(".modal").forEach(function(m) { document.body.appendChild(m); }); });</script>\n</body>')
            c = c.replace('style.css"', 'style.css?v=2.1"')
            with open(p, 'w', encoding='utf-8') as f_out:
                f_out.write(c)
