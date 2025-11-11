// Limit each description to 200 characters
document.querySelectorAll(".description").forEach((desc) => {
  const fullText = desc.textContent.trim();
  if (fullText.length > 200) {
    desc.textContent = fullText.substring(0, 200) + "...";
  }
});
