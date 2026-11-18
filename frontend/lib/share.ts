export function whatsappShareUrl(title: string, pageUrl: string): string {
  return `https://wa.me/?text=${encodeURIComponent(`${title} — our weekend, recut as a blockbuster. ${pageUrl}`)}`;
}

export async function shareForInstagram(title: string, trailerUrl: string): Promise<string> {
  const text = `${title} — our weekend, recut as a blockbuster.`;
  if (navigator.share) {
    await navigator.share({ title, text, url: trailerUrl });
    return "Share sheet opened.";
  }
  const anchor = document.createElement("a");
  anchor.href = trailerUrl;
  anchor.download = "cutline-trailer.mp4";
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  try {
    await navigator.clipboard.writeText(text);
    return "Trailer downloaded and caption copied. Add it to your Instagram story or reel.";
  } catch {
    return "Trailer downloaded. Add it to your Instagram story or reel.";
  }
}
