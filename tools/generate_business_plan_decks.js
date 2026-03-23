const fs = require("fs");
const path = require("path");
const ROOT = path.resolve(__dirname, "..");
const PPT_NS = "http://schemas.openxmlformats.org/presentationml/2006/main";
const DRAW_NS = "http://schemas.openxmlformats.org/drawingml/2006/main";
const REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships";
const PKG_REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships";

const SLIDE_W = 12192000;
const SLIDE_H = 6858000;
const COLOR = {
  bg: "F8F5EF",
  dark: "173042",
  band: "0E3141",
  accent: "17807A",
  gold: "C59B62",
  white: "FFFFFF",
  muted: "6A7781",
};

const TRACE_FILE = path.join(ROOT, "output", "ppt_trace.txt");

function trace(message) {
  fs.mkdirSync(path.join(ROOT, "output"), { recursive: true });
  fs.appendFileSync(TRACE_FILE, `${message}\n`, "utf8");
}

const decks = [
  {
    source: path.join(ROOT, "docs", "presentations", "specialist_ai_os_internal_deck_v0_1.md"),
    buildDir: path.join(ROOT, "docs", "presentations", "build", "specialist_ai_os_internal_deck_v0_1"),
    output: path.join(ROOT, "docs", "presentations", "specialist_ai_os_internal_deck_v0_1.pptx"),
    label: "INTERNAL",
    subject: "specialist-ai-os internal business plan deck",
  },
  {
    source: path.join(ROOT, "docs", "presentations", "specialist_ai_os_external_deck_v0_1.md"),
    buildDir: path.join(ROOT, "docs", "presentations", "build", "specialist_ai_os_external_deck_v0_1"),
    output: path.join(ROOT, "docs", "presentations", "specialist_ai_os_external_deck_v0_1.pptx"),
    label: "EXTERNAL",
    subject: "specialist-ai-os external business plan deck",
  },
];

function escapeXml(value) {
  return value
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&apos;");
}

function writeFile(targetPath, contents) {
  fs.mkdirSync(path.dirname(targetPath), { recursive: true });
  fs.writeFileSync(targetPath, contents, "utf8");
}

function parseSlides(markdown) {
  return markdown
    .split(/\r?\n---\r?\n/)
    .map((chunk) => chunk.trim())
    .filter(Boolean)
    .map((chunk) => {
      const lines = chunk.split(/\r?\n/);
      let title = "";
      const body = [];

      for (const rawLine of lines) {
        const line = rawLine.trimEnd();
        if (!title && line.startsWith("# ")) {
          title = line.slice(2).trim();
          continue;
        }
        if (!title && line.trim()) {
          title = line.trim();
          continue;
        }
        body.push(line);
      }

      return { title, body };
    });
}

function paragraphXml(text, options = {}) {
  if (text === "") {
    return "<a:p><a:endParaRPr lang=\"ja-JP\"/></a:p>";
  }

  const {
    fontSize = 1800,
    color = COLOR.dark,
    bold = false,
    align = "l",
  } = options;

  return [
    `<a:p>`,
    `<a:pPr algn="${align}"/>`,
    `<a:r>`,
    `<a:rPr lang="ja-JP" sz="${fontSize}"${bold ? " b=\"1\"" : ""} dirty="0">`,
    `<a:solidFill><a:srgbClr val="${color}"/></a:solidFill>`,
    `</a:rPr>`,
    `<a:t>${escapeXml(text)}</a:t>`,
    `</a:r>`,
    `<a:endParaRPr lang="ja-JP" sz="${fontSize}"/>`,
    `</a:p>`,
  ].join("");
}

function textShapeXml(id, name, x, y, w, h, paragraphs, options = {}) {
  const {
    fontSize = 1800,
    color = COLOR.dark,
    bold = false,
    align = "l",
  } = options;

  const body = paragraphs
    .map((line) => paragraphXml(line, { fontSize, color, bold, align }))
    .join("");

  return [
    `<p:sp>`,
    `<p:nvSpPr>`,
    `<p:cNvPr id="${id}" name="${escapeXml(name)}"/>`,
    `<p:cNvSpPr txBox="1"/>`,
    `<p:nvPr/>`,
    `</p:nvSpPr>`,
    `<p:spPr>`,
    `<a:xfrm><a:off x="${x}" y="${y}"/><a:ext cx="${w}" cy="${h}"/></a:xfrm>`,
    `<a:prstGeom prst="rect"><a:avLst/></a:prstGeom>`,
    `<a:noFill/>`,
    `<a:ln><a:noFill/></a:ln>`,
    `</p:spPr>`,
    `<p:txBody>`,
    `<a:bodyPr wrap="square" anchor="t" rtlCol="0"><a:normAutofit/></a:bodyPr>`,
    `<a:lstStyle/>`,
    body,
    `</p:txBody>`,
    `</p:sp>`,
  ].join("");
}

function rectShapeXml(id, name, x, y, w, h, fill) {
  return [
    `<p:sp>`,
    `<p:nvSpPr>`,
    `<p:cNvPr id="${id}" name="${escapeXml(name)}"/>`,
    `<p:cNvSpPr/>`,
    `<p:nvPr/>`,
    `</p:nvSpPr>`,
    `<p:spPr>`,
    `<a:xfrm><a:off x="${x}" y="${y}"/><a:ext cx="${w}" cy="${h}"/></a:xfrm>`,
    `<a:prstGeom prst="rect"><a:avLst/></a:prstGeom>`,
    `<a:solidFill><a:srgbClr val="${fill}"/></a:solidFill>`,
    `<a:ln><a:noFill/></a:ln>`,
    `</p:spPr>`,
    `</p:sp>`,
  ].join("");
}

function slideXml(slide, index, deckLabel, totalSlides) {
  const isTitle = index === 0;
  const shapes = [];

  shapes.push(rectShapeXml(2, "Background", 0, 0, SLIDE_W, SLIDE_H, isTitle ? COLOR.band : COLOR.bg));

  if (isTitle) {
    shapes.push(rectShapeXml(3, "Accent", 822960, 1714500, 3657600, 137160, COLOR.gold));
    shapes.push(
      textShapeXml(4, "Title", 822960, 2011680, 10363200, 1219200, [slide.title], {
        fontSize: 3000,
        color: COLOR.white,
        bold: true,
        align: "l",
      })
    );
    shapes.push(
      textShapeXml(5, "Subtitle", 822960, 3200400, 10363200, 1828800, slide.body.filter((line) => line.trim()), {
        fontSize: 1800,
        color: "EDE7DD",
        align: "l",
      })
    );
  } else {
    shapes.push(rectShapeXml(3, "Top Band", 0, 0, SLIDE_W, 411480, COLOR.band));
    shapes.push(
      textShapeXml(4, "Deck Label", 10058400, 137160, 1188720, 182880, [deckLabel], {
        fontSize: 900,
        color: COLOR.white,
        bold: true,
        align: "r",
      })
    );
    shapes.push(
      textShapeXml(5, "Title", 685800, 594360, 10896600, 685800, [slide.title], {
        fontSize: 2200,
        color: COLOR.dark,
        bold: true,
      })
    );

    const bodyLines = [];
    for (const rawLine of slide.body) {
      if (!rawLine.trim()) {
        bodyLines.push("");
      } else if (rawLine.startsWith("- ")) {
        bodyLines.push(`• ${rawLine.slice(2).trim()}`);
      } else {
        bodyLines.push(rawLine.trim());
      }
    }

    shapes.push(
      textShapeXml(6, "Body", 822960, 1463040, 10363200, 4572000, bodyLines, {
        fontSize: 1700,
        color: COLOR.dark,
      })
    );
    shapes.push(
      textShapeXml(7, "Footer", 822960, 6172200, 10363200, 228600, [`${index + 1} / ${totalSlides}`], {
        fontSize: 900,
        color: COLOR.muted,
        align: "r",
      })
    );
  }

  return [
    `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>`,
    `<p:sld xmlns:a="${DRAW_NS}" xmlns:r="${REL_NS}" xmlns:p="${PPT_NS}">`,
    `<p:cSld>`,
    `<p:spTree>`,
    `<p:nvGrpSpPr>`,
    `<p:cNvPr id="1" name=""/>`,
    `<p:cNvGrpSpPr/>`,
    `<p:nvPr/>`,
    `</p:nvGrpSpPr>`,
    `<p:grpSpPr>`,
    `<a:xfrm><a:off x="0" y="0"/><a:ext cx="0" cy="0"/><a:chOff x="0" y="0"/><a:chExt cx="0" cy="0"/></a:xfrm>`,
    `</p:grpSpPr>`,
    shapes.join(""),
    `</p:spTree>`,
    `</p:cSld>`,
    `<p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr>`,
    `</p:sld>`,
  ].join("");
}

function slideRelsXml() {
  return [
    `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>`,
    `<Relationships xmlns="${PKG_REL_NS}">`,
    `<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideLayout" Target="../slideLayouts/slideLayout1.xml"/>`,
    `</Relationships>`,
  ].join("");
}

function contentTypesXml(slideCount) {
  const slideOverrides = Array.from({ length: slideCount }, (_, index) => {
    return `<Override PartName="/ppt/slides/slide${index + 1}.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slide+xml"/>`;
  }).join("");

  return [
    `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>`,
    `<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">`,
    `<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>`,
    `<Default Extension="xml" ContentType="application/xml"/>`,
    `<Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/>`,
    `<Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>`,
    `<Override PartName="/ppt/presentation.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.presentation.main+xml"/>`,
    `<Override PartName="/ppt/slideMasters/slideMaster1.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slideMaster+xml"/>`,
    `<Override PartName="/ppt/slideLayouts/slideLayout1.xml" ContentType="application/vnd.openxmlformats-officedocument.presentationml.slideLayout+xml"/>`,
    `<Override PartName="/ppt/theme/theme1.xml" ContentType="application/vnd.openxmlformats-officedocument.theme+xml"/>`,
    slideOverrides,
    `</Types>`,
  ].join("");
}

function rootRelsXml() {
  return [
    `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>`,
    `<Relationships xmlns="${PKG_REL_NS}">`,
    `<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="ppt/presentation.xml"/>`,
    `<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>`,
    `<Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" Target="docProps/app.xml"/>`,
    `</Relationships>`,
  ].join("");
}

function appXml(slides) {
  const titleParts = slides
    .map((slide) => `<vt:lpstr>${escapeXml(slide.title)}</vt:lpstr>`)
    .join("");

  return [
    `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>`,
    `<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties" xmlns:vt="http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes">`,
    `<Application>Codex</Application>`,
    `<PresentationFormat>On-screen Show (16:9)</PresentationFormat>`,
    `<Slides>${slides.length}</Slides>`,
    `<Notes>0</Notes>`,
    `<HiddenSlides>0</HiddenSlides>`,
    `<MMClips>0</MMClips>`,
    `<ScaleCrop>false</ScaleCrop>`,
    `<HeadingPairs>`,
    `<vt:vector size="2" baseType="variant">`,
    `<vt:variant><vt:lpstr>タイトル</vt:lpstr></vt:variant>`,
    `<vt:variant><vt:i4>${slides.length}</vt:i4></vt:variant>`,
    `</vt:vector>`,
    `</HeadingPairs>`,
    `<TitlesOfParts><vt:vector size="${slides.length}" baseType="lpstr">${titleParts}</vt:vector></TitlesOfParts>`,
    `<Company>OpenAI</Company>`,
    `<LinksUpToDate>false</LinksUpToDate>`,
    `<SharedDoc>false</SharedDoc>`,
    `<HyperlinksChanged>false</HyperlinksChanged>`,
    `<AppVersion>16.0000</AppVersion>`,
    `</Properties>`,
  ].join("");
}

function coreXml(title, subject) {
  const created = new Date().toISOString();
  return [
    `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>`,
    `<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/" xmlns:dcmitype="http://purl.org/dc/dcmitype/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">`,
    `<dc:title>${escapeXml(title)}</dc:title>`,
    `<dc:subject>${escapeXml(subject)}</dc:subject>`,
    `<dc:creator>Codex</dc:creator>`,
    `<cp:lastModifiedBy>Codex</cp:lastModifiedBy>`,
    `<dcterms:created xsi:type="dcterms:W3CDTF">${created}</dcterms:created>`,
    `<dcterms:modified xsi:type="dcterms:W3CDTF">${created}</dcterms:modified>`,
    `</cp:coreProperties>`,
  ].join("");
}

function presentationXml(slideCount) {
  const slideIds = Array.from({ length: slideCount }, (_, index) => {
    return `<p:sldId id="${256 + index}" r:id="rId${index + 2}"/>`;
  }).join("");

  return [
    `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>`,
    `<p:presentation xmlns:a="${DRAW_NS}" xmlns:r="${REL_NS}" xmlns:p="${PPT_NS}">`,
    `<p:sldMasterIdLst><p:sldMasterId id="2147483648" r:id="rId1"/></p:sldMasterIdLst>`,
    `<p:sldIdLst>${slideIds}</p:sldIdLst>`,
    `<p:sldSz cx="${SLIDE_W}" cy="${SLIDE_H}"/>`,
    `<p:notesSz cx="6858000" cy="9144000"/>`,
    `<p:defaultTextStyle>`,
    `<a:defPPr/>`,
    `<a:lvl1pPr marL="0" indent="0"><a:defRPr sz="1800"/></a:lvl1pPr>`,
    `<a:lvl2pPr marL="0" indent="0"><a:defRPr sz="1600"/></a:lvl2pPr>`,
    `</p:defaultTextStyle>`,
    `</p:presentation>`,
  ].join("");
}

function presentationRelsXml(slideCount) {
  const slideRels = Array.from({ length: slideCount }, (_, index) => {
    return `<Relationship Id="rId${index + 2}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slide" Target="slides/slide${index + 1}.xml"/>`;
  }).join("");

  return [
    `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>`,
    `<Relationships xmlns="${PKG_REL_NS}">`,
    `<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideMaster" Target="slideMasters/slideMaster1.xml"/>`,
    slideRels,
    `</Relationships>`,
  ].join("");
}

function slideMasterXml() {
  return [
    `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>`,
    `<p:sldMaster xmlns:a="${DRAW_NS}" xmlns:r="${REL_NS}" xmlns:p="${PPT_NS}">`,
    `<p:cSld name="Master">`,
    `<p:spTree>`,
    `<p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr>`,
    `<p:grpSpPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="0" cy="0"/><a:chOff x="0" y="0"/><a:chExt cx="0" cy="0"/></a:xfrm></p:grpSpPr>`,
    `</p:spTree>`,
    `</p:cSld>`,
    `<p:clrMap bg1="lt1" tx1="dk1" bg2="lt2" tx2="dk2" accent1="accent1" accent2="accent2" accent3="accent3" accent4="accent4" accent5="accent5" accent6="accent6" hlink="hlink" folHlink="folHlink"/>`,
    `<p:sldLayoutIdLst><p:sldLayoutId id="2147483649" r:id="rId1"/></p:sldLayoutIdLst>`,
    `<p:txStyles>`,
    `<p:titleStyle><a:lvl1pPr algn="l"><a:defRPr sz="2800" b="1"/></a:lvl1pPr></p:titleStyle>`,
    `<p:bodyStyle><a:lvl1pPr marL="0" indent="0" algn="l"><a:defRPr sz="1800"/></a:lvl1pPr></p:bodyStyle>`,
    `<p:otherStyle><a:defPPr/><a:lvl1pPr marL="0" indent="0"><a:defRPr sz="1800"/></a:lvl1pPr></p:otherStyle>`,
    `</p:txStyles>`,
    `</p:sldMaster>`,
  ].join("");
}

function slideMasterRelsXml() {
  return [
    `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>`,
    `<Relationships xmlns="${PKG_REL_NS}">`,
    `<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideLayout" Target="../slideLayouts/slideLayout1.xml"/>`,
    `<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/theme" Target="../theme/theme1.xml"/>`,
    `</Relationships>`,
  ].join("");
}

function slideLayoutXml() {
  return [
    `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>`,
    `<p:sldLayout xmlns:a="${DRAW_NS}" xmlns:r="${REL_NS}" xmlns:p="${PPT_NS}" type="blank" preserve="1">`,
    `<p:cSld name="Blank">`,
    `<p:spTree>`,
    `<p:nvGrpSpPr><p:cNvPr id="1" name=""/><p:cNvGrpSpPr/><p:nvPr/></p:nvGrpSpPr>`,
    `<p:grpSpPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="0" cy="0"/><a:chOff x="0" y="0"/><a:chExt cx="0" cy="0"/></a:xfrm></p:grpSpPr>`,
    `</p:spTree>`,
    `</p:cSld>`,
    `<p:clrMapOvr><a:masterClrMapping/></p:clrMapOvr>`,
    `</p:sldLayout>`,
  ].join("");
}

function slideLayoutRelsXml() {
  return [
    `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>`,
    `<Relationships xmlns="${PKG_REL_NS}">`,
    `<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/slideMaster" Target="../slideMasters/slideMaster1.xml"/>`,
    `</Relationships>`,
  ].join("");
}

function themeXml() {
  return [
    `<?xml version="1.0" encoding="UTF-8" standalone="yes"?>`,
    `<a:theme xmlns:a="${DRAW_NS}" name="specialist-ai-os Theme">`,
    `<a:themeElements>`,
    `<a:clrScheme name="specialist-ai-os">`,
    `<a:dk1><a:srgbClr val="${COLOR.dark}"/></a:dk1>`,
    `<a:lt1><a:srgbClr val="${COLOR.white}"/></a:lt1>`,
    `<a:dk2><a:srgbClr val="${COLOR.band}"/></a:dk2>`,
    `<a:lt2><a:srgbClr val="${COLOR.bg}"/></a:lt2>`,
    `<a:accent1><a:srgbClr val="${COLOR.accent}"/></a:accent1>`,
    `<a:accent2><a:srgbClr val="${COLOR.gold}"/></a:accent2>`,
    `<a:accent3><a:srgbClr val="7C8A96"/></a:accent3>`,
    `<a:accent4><a:srgbClr val="D97C54"/></a:accent4>`,
    `<a:accent5><a:srgbClr val="9D6C8B"/></a:accent5>`,
    `<a:accent6><a:srgbClr val="4C6E91"/></a:accent6>`,
    `<a:hlink><a:srgbClr val="0563C1"/></a:hlink>`,
    `<a:folHlink><a:srgbClr val="954F72"/></a:folHlink>`,
    `</a:clrScheme>`,
    `<a:fontScheme name="specialist-ai-os Fonts">`,
    `<a:majorFont><a:latin typeface="Yu Gothic"/><a:ea typeface="Yu Gothic"/><a:cs typeface="Yu Gothic"/></a:majorFont>`,
    `<a:minorFont><a:latin typeface="Yu Gothic"/><a:ea typeface="Yu Gothic"/><a:cs typeface="Yu Gothic"/></a:minorFont>`,
    `</a:fontScheme>`,
    `<a:fmtScheme name="specialist-ai-os Format">`,
    `<a:fillStyleLst>`,
    `<a:solidFill><a:schemeClr val="phClr"/></a:solidFill>`,
    `<a:solidFill><a:schemeClr val="accent1"/></a:solidFill>`,
    `<a:solidFill><a:schemeClr val="accent2"/></a:solidFill>`,
    `</a:fillStyleLst>`,
    `<a:lnStyleLst>`,
    `<a:ln w="9525"><a:solidFill><a:schemeClr val="phClr"/></a:solidFill><a:prstDash val="solid"/></a:ln>`,
    `<a:ln w="25400"><a:solidFill><a:schemeClr val="phClr"/></a:solidFill><a:prstDash val="solid"/></a:ln>`,
    `<a:ln w="38100"><a:solidFill><a:schemeClr val="phClr"/></a:solidFill><a:prstDash val="solid"/></a:ln>`,
    `</a:lnStyleLst>`,
    `<a:effectStyleLst><a:effectStyle><a:effectLst/></a:effectStyle><a:effectStyle><a:effectLst/></a:effectStyle><a:effectStyle><a:effectLst/></a:effectStyle></a:effectStyleLst>`,
    `<a:bgFillStyleLst>`,
    `<a:solidFill><a:schemeClr val="lt1"/></a:solidFill>`,
    `<a:solidFill><a:schemeClr val="lt2"/></a:solidFill>`,
    `<a:solidFill><a:schemeClr val="accent1"/></a:solidFill>`,
    `</a:bgFillStyleLst>`,
    `</a:fmtScheme>`,
    `</a:themeElements>`,
    `<a:objectDefaults/>`,
    `<a:extraClrSchemeLst/>`,
    `</a:theme>`,
  ].join("");
}

function packageDeck(deck) {
  trace(`start:${deck.source}`);
  const markdown = fs.readFileSync(deck.source, "utf8");
  const slides = parseSlides(markdown);
  trace(`parsed:${slides.length}`);
  const buildDir = deck.buildDir;

  fs.mkdirSync(buildDir, { recursive: true });
  trace(`mkdir:${buildDir}`);

  writeFile(path.join(buildDir, "[Content_Types].xml"), contentTypesXml(slides.length));
  trace("wrote:content_types");
  writeFile(path.join(buildDir, "_rels", ".rels"), rootRelsXml());
  writeFile(path.join(buildDir, "docProps", "app.xml"), appXml(slides));
  writeFile(path.join(buildDir, "docProps", "core.xml"), coreXml(slides[0].title, deck.subject));
  writeFile(path.join(buildDir, "ppt", "presentation.xml"), presentationXml(slides.length));
  writeFile(path.join(buildDir, "ppt", "_rels", "presentation.xml.rels"), presentationRelsXml(slides.length));
  writeFile(path.join(buildDir, "ppt", "slideMasters", "slideMaster1.xml"), slideMasterXml());
  writeFile(path.join(buildDir, "ppt", "slideMasters", "_rels", "slideMaster1.xml.rels"), slideMasterRelsXml());
  writeFile(path.join(buildDir, "ppt", "slideLayouts", "slideLayout1.xml"), slideLayoutXml());
  writeFile(path.join(buildDir, "ppt", "slideLayouts", "_rels", "slideLayout1.xml.rels"), slideLayoutRelsXml());
  writeFile(path.join(buildDir, "ppt", "theme", "theme1.xml"), themeXml());

  slides.forEach((slide, index) => {
    writeFile(
      path.join(buildDir, "ppt", "slides", `slide${index + 1}.xml`),
      slideXml(slide, index, deck.label, slides.length)
    );
    writeFile(
      path.join(buildDir, "ppt", "slides", "_rels", `slide${index + 1}.xml.rels`),
      slideRelsXml()
    );
  });
  trace(`done:${buildDir}`);
  console.log(`Prepared ${buildDir}`);
}

try {
  if (fs.existsSync(TRACE_FILE)) {
    fs.unlinkSync(TRACE_FILE);
  }
  for (const deck of decks) {
    packageDeck(deck);
  }
} catch (error) {
  const message = error && error.stack ? error.stack : String(error);
  fs.mkdirSync(path.join(ROOT, "output"), { recursive: true });
  fs.writeFileSync(path.join(ROOT, "output", "ppt_error.txt"), message, "utf8");
  console.error(message);
  process.exit(1);
}
