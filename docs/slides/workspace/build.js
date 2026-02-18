const pptxgen = require('pptxgenjs');
const html2pptx = require('/usr/local/google/home/jwortz/.claude/skills/pptx/scripts/html2pptx');
const path = require('path');

async function createPresentation() {
    const pptx = new pptxgen();
    pptx.layout = 'LAYOUT_16x9';
    pptx.author = 'Google Cloud';
    pptx.title = 'Gemini Enterprise Workshop: Grocery Retail';
    pptx.subject = 'Agentic AI for Store Operations';

    const dir = __dirname;

    // Slide 1: Title
    await html2pptx(path.join(dir, 'slide01.html'), pptx);

    // Slide 2: Business Problem
    await html2pptx(path.join(dir, 'slide02.html'), pptx);

    // Slide 3: Platform Overview (with table)
    const { slide: slide3, placeholders: ph3 } = await html2pptx(path.join(dir, 'slide03.html'), pptx);
    const capData = [
        [
            { text: "Capability", options: { fill: { color: "4285F4" }, color: "FFFFFF", bold: true, fontSize: 11 } },
            { text: "What It Does", options: { fill: { color: "4285F4" }, color: "FFFFFF", bold: true, fontSize: 11 } },
            { text: "Sarah's Use Case", options: { fill: { color: "4285F4" }, color: "FFFFFF", bold: true, fontSize: 11 } }
        ],
        ["Shopper Simulator", "AI-powered A/B testing of store layouts", "Test endcap before deployment"],
        ["Discovery Engine", "Enterprise search over SOPs and docs", "Brand guideline compliance"],
        ["Agent Engine", "Multi-agent AI orchestration", "Route analytics, search, image gen"],
        ["BigQuery + MCP", "Natural language data analytics", "Sales trends by store/product"],
        ["Gemini 3 Pro Image", "Brand-compliant product imagery", "Marketing visuals for endcap"],
        ["Memory Bank", "Cross-session user memory", "Remember store preferences"],
        ["Model Armor", "Content safety and PII protection", "Protect loyalty data"],
        ["A2A Protocol", "Agent-to-agent communication", "Cross-team simulator reuse"],
        ["ADK Evaluation", "Agent testing and simulation", "378 automated tests"]
    ];
    if (ph3.length > 0) {
        slide3.addTable(capData, {
            ...ph3[0],
            border: { pt: 0.5, color: "DADCE0" },
            colW: [2.0, 3.5, 3.3],
            rowH: [0.35, 0.3, 0.3, 0.3, 0.3, 0.3, 0.3, 0.3, 0.3, 0.3],
            fontSize: 9,
            valign: "middle",
            autoPage: false
        });
    }

    // Slide 4: Architecture
    await html2pptx(path.join(dir, 'slide04.html'), pptx);

    // Slide 5: Act 1 Simulator
    await html2pptx(path.join(dir, 'slide05.html'), pptx);

    // Slide 6: Act 1 Results
    await html2pptx(path.join(dir, 'slide06.html'), pptx);

    // Slide 7: Act 2 Brand
    await html2pptx(path.join(dir, 'slide07.html'), pptx);

    // Slide 8: Act 2 Image Gen
    await html2pptx(path.join(dir, 'slide08.html'), pptx);

    // Slide 9: Act 3 Analytics
    await html2pptx(path.join(dir, 'slide09.html'), pptx);

    // Slide 10: Act 3 MCP
    await html2pptx(path.join(dir, 'slide10.html'), pptx);

    // Slide 11: Act 4 Model Armor
    await html2pptx(path.join(dir, 'slide11.html'), pptx);

    // Slide 12: Act 4 Evaluation
    await html2pptx(path.join(dir, 'slide12.html'), pptx);

    // Slide 13: Act 5 A2A
    await html2pptx(path.join(dir, 'slide13.html'), pptx);

    // Slide 14: Act 6 Business Impact (with table)
    const { slide: slide14, placeholders: ph14 } = await html2pptx(path.join(dir, 'slide14.html'), pptx);
    const impactData = [
        [
            { text: "Metric", options: { fill: { color: "4285F4" }, color: "FFFFFF", bold: true, fontSize: 12 } },
            { text: "Before (Manual)", options: { fill: { color: "4285F4" }, color: "FFFFFF", bold: true, fontSize: 12 } },
            { text: "After (AI-Powered)", options: { fill: { color: "4285F4" }, color: "FFFFFF", bold: true, fontSize: 12 } }
        ],
        ["Strategy testing", "2-3 weeks per test", "Minutes per simulation"],
        ["SOP lookup", "15 min (paper binders)", "30 seconds (grounded search)"],
        ["Brand compliance", "Manual review", "Automated verification"],
        ["Analytics access", "Requires analyst / SQL", "Self-service natural language"],
        ["Content safety", "Application-level checks", "Infrastructure-level (Model Armor)"],
        ["Cross-team reuse", "Email / meetings", "A2A agent discovery"]
    ];
    if (ph14.length > 0) {
        slide14.addTable(impactData, {
            ...ph14[0],
            border: { pt: 0.5, color: "DADCE0" },
            colW: [2.5, 3.2, 3.2],
            rowH: [0.4, 0.35, 0.35, 0.35, 0.35, 0.35, 0.35],
            fontSize: 11,
            valign: "middle",
            autoPage: false
        });
    }

    // Slide 15: Agent Engine Console
    await html2pptx(path.join(dir, 'slide15.html'), pptx);

    // Slide 16: Observability
    await html2pptx(path.join(dir, 'slide16.html'), pptx);

    // Slide 17: Getting Started
    await html2pptx(path.join(dir, 'slide17.html'), pptx);

    // Slide 18: Next Steps
    await html2pptx(path.join(dir, 'slide18.html'), pptx);

    // Save
    const outPath = path.join(dir, '..', 'gemini_enterprise_workshop.pptx');
    await pptx.writeFile({ fileName: outPath });
    console.log('Presentation created: ' + outPath);
}

createPresentation().catch(err => {
    console.error('Error:', err.message || err);
    process.exit(1);
});
