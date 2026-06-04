const fs = require("fs");
const path = require("path");

const root = path.resolve(__dirname, "..");
const policy = JSON.parse(fs.readFileSync(path.join(root, "config", "alert_policy.json"), "utf8"));
const feeds = JSON.parse(fs.readFileSync(path.join(root, "config", "feed_layers.json"), "utf8"));

function flattenSources() {
  const sourceMap = new Map();
  for (const layer of feeds.layers) {
    for (const feed of layer.feeds) {
      sourceMap.set(feed.id, {
        layer: layer.id,
        weight: feed.weight || layer.defaultWeight,
        name: feed.name
      });
    }
  }
  return sourceMap;
}

function countMatches(text, terms) {
  const lower = text.toLowerCase();
  return terms.filter((term) => lower.includes(term.toLowerCase())).length;
}

function scoreEvent({ sourceId, title, summary = "", sensitivity = "balanced" }) {
  const sources = flattenSources();
  const source = sources.get(sourceId) || { layer: "news_validation", weight: 50, name: sourceId };
  const text = `${title} ${summary}`;
  let keywordScore = 0;
  const matched = {};

  for (const [group, config] of Object.entries(policy.keywordWeights)) {
    const matches = countMatches(text, config.terms);
    matched[group] = matches;
    if (matches > 0) {
      keywordScore += config.weight * Math.min(matches, 2);
    }
  }

  const sourceBase = Math.min(source.weight / 2, 50);
  const multiplier = policy.sourceMultipliers[source.layer] || 1;
  const rawScore = Math.round((sourceBase + keywordScore) * multiplier);
  const score = Math.max(0, Math.min(100, rawScore));
  const profile = policy.sensitivityProfiles[sensitivity] || policy.sensitivityProfiles.balanced;
  const level = policy.alertLevels.find((item) => score >= item.scoreRange[0] && score <= item.scoreRange[1]);

  return {
    source: source.name,
    sourceLayer: source.layer,
    sensitivity,
    score,
    alertLevel: level ? level.level : "GREEN",
    shouldAlert: score >= profile.minScore,
    matched
  };
}

if (require.main === module) {
  const [sourceId, ...titleParts] = process.argv.slice(2);
  const title = titleParts.join(" ");

  if (!sourceId || !title) {
    console.error('Usage: node scripts/score-event.js <sourceId> "<headline text>"');
    process.exit(1);
  }

  console.log(JSON.stringify(scoreEvent({ sourceId, title }), null, 2));
}

module.exports = { scoreEvent };

