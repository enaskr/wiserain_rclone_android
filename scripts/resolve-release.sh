#!/usr/bin/env bash
set -euo pipefail
: "${GH_TOKEN:?GH_TOKEN is required}"
: "${GH_REPO:?GH_REPO is required}"
: "${GITHUB_OUTPUT:?GITHUB_OUTPUT is required}"
: "${GITHUB_STEP_SUMMARY:?GITHUB_STEP_SUMMARY is required}"

if [[ -n "${REQUESTED_TAG:-}" ]]; then
  tag="$REQUESTED_TAG"
  [[ "$tag" =~ ^[A-Za-z0-9._-]+$ ]] || { echo "Invalid release tag" >&2; exit 1; }
  tag="$(gh api "repos/wiserain/rclone/releases/tags/$tag" --jq '.tag_name')"
else
  tag="$(gh api repos/wiserain/rclone/releases/latest --jq '.tag_name')"
fi
[[ "$tag" =~ ^[A-Za-z0-9._-]+$ ]] || { echo 'Invalid release tag' >&2; exit 1; }

ref_json="$(gh api "repos/wiserain/rclone/git/ref/tags/$tag")"
kind="$(jq -r '.object.type' <<< "$ref_json")"
sha="$(jq -r '.object.sha' <<< "$ref_json")"
for _ in {1..6}; do
  [[ "$kind" != tag ]] && break
  annotated="$(gh api "repos/wiserain/rclone/git/tags/$sha")"
  kind="$(jq -r '.object.type' <<< "$annotated")"
  sha="$(jq -r '.object.sha' <<< "$annotated")"
done
if [[ "$kind" != commit || ! "$sha" =~ ^[a-f0-9]{40}$ ]]; then
  echo "Failed to resolve Git commit for release $tag" >&2
  exit 1
fi

# Completed builds are recorded as repository Releases named aar-<upstream-tag>.
# A release is considered successful only when it contains an actual .aar asset.
# Fetching this list must succeed: network/auth errors must not cause a rebuild.
all_releases="$(gh api --paginate "repos/$GH_REPO/releases?per_page=100" | jq -s 'add // []')"
successful_releases="$(jq -c '[.[]
  | select(.draft == false and (.tag_name | startswith("aar-")))
  | select(any(.assets[]?; .name | endswith(".aar")))
]' <<< "$all_releases")"

# The most recent successful AAR Release is the persisted previous version.
previous_tag="$(jq -r 'sort_by(.published_at // .created_at) | last | .tag_name // ""' <<< "$successful_releases")"
previous_version="${previous_tag#aar-}"

build=true
reason="No completed AAR release exists for this upstream version"
if [[ -n "$previous_version" && "$tag" == "$previous_version" ]]; then
  build=false
  reason="Upstream version matches the last successful AAR release"
elif jq -e --arg wanted "aar-$tag" 'any(.[]; .tag_name == $wanted)' <<< "$successful_releases" >/dev/null; then
  build=false
  reason="This upstream version already has a successful AAR release"
fi

{
  printf 'tag=%s\n' "$tag"
  printf 'sha=%s\n' "$sha"
  printf 'build=%s\n' "$build"
} >> "$GITHUB_OUTPUT"
{
  echo '## Upstream release version check'
  echo "- Latest/selected upstream version: $tag"
  echo "- Last successfully published version: ${previous_version:-none}"
  echo "- Build required: $build"
  echo "- Reason: $reason"
  echo "- Upstream commit: $sha"
} >> "$GITHUB_STEP_SUMMARY"
