#!/usr/bin/env python3
"""
旺财工具箱 — 测试工程师 Agent
每次修改代码后运行:  python3 .audit/test.py
检查所有页面的结构一致性、CSS 冲突、基础功能。
"""

import os, re, sys
from collections import Counter, defaultdict

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ISSUES = []

def P0(filepath, msg):
    ISSUES.append(("P0", filepath, msg))

def P1(filepath, msg):
    ISSUES.append(("P1", filepath, msg))

def P2(filepath, msg):
    ISSUES.append(("P2", filepath, msg))

def get_pages():
    """Return all HTML pages"""
    pages = []
    for root, dirs, files in os.walk(BASE):
        dirs[:] = [d for d in dirs if not d.startswith('.') and d != '.git']
        for f in sorted(files):
            if f.endswith('.html'):
                pages.append(os.path.join(root, f))
    return pages

def check_page(filepath):
    rel = os.path.relpath(filepath, BASE)
    with open(filepath, 'r') as f:
        html = f.read()
    
    # ── CSS ──
    # Check for CSS link
    if 'assets/css/style.css' not in html:
        P0(rel, "Missing shared CSS link")
    
    # Check for conflicting CSS variables
    # Shared uses --color-accent, old pages use --accent
    # Tool pages intentionally use different --accent for branding (image=orange, pdf=purple)
    is_tool_page = any(t in rel for t in ['-toolbox/', '-compress/', '-tools/'])
    
    has_legacy_bg = re.search(r'(?<!color-)--bg\s*:', html)
    has_legacy_card = re.search(r'(?<!color-)--card\s*:', html)
    
    # Only flag accent mismatch on non-tool pages (tools need their brand color)
    has_color_accent = '--color-accent' in html
    has_legacy_accent = re.search(r'(?<!color-)--accent\s*:', html)
    if has_legacy_accent and has_color_accent and not is_tool_page:
        m1 = re.search(r'--color-accent\s*:\s*([^;]+)', html)
        m2 = re.search(r'(?<!color-)--accent\s*:\s*([^;]+)', html)
        if m1 and m2:
            v1 = m1.group(1).strip()
            v2 = m2.group(1).strip()
            if v1 != v2:
                P2(rel, f"Accent mismatch (non-tool page): --color-accent={v1} vs --accent={v2}")
    
    # ── PRICING / PAYWALL TEXT ──
    pricing_patterns = [
        r'¥\d+\s*(永久买断|永久解锁|每月|/月)',  # ¥6 永久买断
        r'(Pro|pro)\s*(版|版本)\s*(到手|仅需|只需)',  # Pro 版到手
        r'升级\s*(Pro|pro|会员|付费)',  # 升级Pro
        r'免费版\s*(限制|一次最多)',  # 免费版限制
        r'(解锁|升级|购买)\s*(Pro|pro|会员)',  # 解锁Pro
    ]
    for pattern in pricing_patterns:
        if re.search(pattern, html):
            P0(rel, f"Contains pricing/upgrade text matching: {pattern}")

    # ── LANG BAR ──
    lang_bars = len(re.findall(r'class="lang-bar"', html))
    if lang_bars == 0:
        P1(rel, "Missing lang-bar")
    elif lang_bars > 1:
        P0(rel, f"{lang_bars} duplicate lang-bars")
    
    # Old dark lang bar (should be removed)
    if 'background:#1a1a2e;color:#fff' in html and 'lang-bar' in html:
        P0(rel, "Old dark inline lang bar still present")
    
    # ── NAV ──
    nav_count = len(re.findall(r'class="nav"', html))
    if nav_count == 0:
        P1(rel, "Missing navigation bar")
    
    nav_links = re.findall(r'class="nav-links"[^>]*>(.*?)</div>', html, re.DOTALL)
    if nav_links:
        links = re.findall(r'href="([^"]+)"', nav_links[0])
        if not links:
            P2(rel, "Nav has no links")
    
    # ── PAGE TITLE ──
    title_match = re.search(r'<title>(.*?)</title>', html)
    if title_match:
        title = title_match.group(1)
        if ' — ' in title and title.count(' — ') > 1:
            P2(rel, f"Double separator in title: '{title}'")
        if title.endswith(' — ') or title.startswith(' — '):
            P2(rel, f"Title has trailing/leading separator")
        if 'DeeperAI Tools — DeeperAI Tools' in title:
            P1(rel, f"Title brand name duplicated: '{title}'")
    
    # ── META ──
    if '<meta name="description"' not in html:
        P1(rel, "Missing meta description")
    if '<link rel="canonical"' not in html:
        P2(rel, "Missing canonical URL")
    if 'og:title' not in html:
        P2(rel, "Missing OG tags")
    
    # ── STRUCTURE ──
    # Check number of </html> tags
    html_close = html.count('</html>')
    if html_close == 0:
        P0(rel, "Missing </html>")
    elif html_close > 1:
        P0(rel, f"{html_close} </html> tags (duplicate)")
    
    body_close = html.count('</body>')
    if body_close == 0:
        P0(rel, "Missing </body>")
    elif body_close > 1:
        P0(rel, f"{body_close} </body> tags (duplicate)")
    
    # ── BLOG ARTICLES ──
    if '/blog/' in rel and 'index.html' not in rel:
        if 'class="article"' not in html:
            P1(rel, "Blog article missing .article wrapper")
    
    # ── TOOL PAGES ──
    if '-toolbox/' in rel or '-compress/' in rel or '-tools/' in rel:
        # Nav should be before header
        nav_pos = html.find('class="nav"')
        header_pos = html.find('class="header"')
        if nav_pos > header_pos and header_pos != -1:
            P0(rel, f"Nav appears AFTER header (nav@byte{nav_pos}, header@byte{header_pos})")
    
    # ── DE/FR STUBS ──
    if '/de/' in rel or '/fr/' in rel:
        if 'Coming soon' in html or 'Cette page' in html or 'noch in Arbeit' in html:
            P2(rel, "Still a stub page (not real content)")
    
    # ── SITEMAP COVERAGE ──
    # Checked separately
    
    return True

def check_sitemap():
    """Verify all pages are in sitemap"""
    sitemap_path = os.path.join(BASE, 'sitemap.xml')
    if not os.path.exists(sitemap_path):
        P0("sitemap.xml", "Missing sitemap.xml")
        return
    
    with open(sitemap_path) as f:
        sitemap = f.read()
    
    urls_in_sitemap = set(re.findall(r'<loc>([^<]+)</loc>', sitemap))
    
    for filepath in get_pages():
        rel = os.path.relpath(filepath, BASE)
        url = f'https://deeperai.cloud/{rel}'
        if '/index.html' in url:
            url = url.replace('/index.html', '/')
        
        if '/admin/' in url:
            continue
        
        if url not in urls_in_sitemap:
            # Try without trailing slash
            if url.rstrip('/') not in [u.rstrip('/') for u in urls_in_sitemap]:
                P2(rel, f"Not in sitemap: {url}")

def check_shared_css():
    """Verify shared CSS loads correct variables"""
    css_path = os.path.join(BASE, 'assets/css/style.css')
    if not os.path.exists(css_path):
        P0("assets/css/style.css", "Shared CSS file missing!")
        return
    
    with open(css_path) as f:
        css = f.read()
    
    required_vars = [
        '--color-accent', '--color-bg', '--color-surface', '--color-border',
        '--color-text', '--color-text-secondary', '--nav-height'
    ]
    for var in required_vars:
        if var not in css:
            P1("assets/css/style.css", f"Missing required CSS variable: {var}")
    
    # Check nav styles
    if '.nav' not in css:
        P0("assets/css/style.css", "Missing .nav styles!")
    if '.lang-bar' not in css:
        P0("assets/css/style.css", "Missing .lang-bar styles!")
    if '.site-footer' not in css:
        P1("assets/css/style.css", "Missing .site-footer styles!")

def main():
    print("🔍 旺财工具箱 — 测试工程师 Agent")
    print(f"   检查 {len(get_pages())} 个页面...")
    print()
    
    for page in get_pages():
        check_page(page)
    
    check_shared_css()
    check_sitemap()
    
    # ── SUMMARY ──
    p0 = [i for i in ISSUES if i[0] == "P0"]
    p1 = [i for i in ISSUES if i[0] == "P1"]
    p2 = [i for i in ISSUES if i[0] == "P2"]
    
    print()
    print("=" * 60)
    print(f"📊 结果: P0={len(p0)}  P1={len(p1)}  P2={len(p2)}  共 {len(ISSUES)} 问题")
    print("=" * 60)
    
    for level, label in [("P0", "🔴 阻断"), ("P1", "🟡 重要"), ("P2", "🔵 小问题")]:
        items = [i for i in ISSUES if i[0] == level]
        if items:
            print(f"\n{label} ({len(items)}):")
            for _, path, msg in items:
                print(f"  {path}")
                print(f"    → {msg}")
    
    print()
    
    exit_code = 1 if p0 else 0
    if exit_code == 0 and not p1 and not p2:
        print("✅ 全站通过！没有问题。")
    elif exit_code == 0:
        print("✅ 无阻断问题。")
    else:
        print("❌ 有阻断问题需要修复！")
    
    return exit_code

if __name__ == '__main__':
    sys.exit(main())
