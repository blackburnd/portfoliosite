// Make the screenshot area or the div containing the 'View Details' button navigate to the same URL
document.addEventListener('DOMContentLoaded', () => {
  const list = document.querySelector('.showcase-list');
  if (!list) return;

  list.addEventListener('click', (e) => {
    // If user clicked a real link, let it behave normally
    if (e.target.closest('a')) return;

    const project = e.target.closest('.showcase-project');
    if (!project) return;

    const clickedScreenshot = e.target.closest('.project-screenshot');
    const clickedActions = e.target.closest('.showcase-actions');

    if (!(clickedScreenshot || clickedActions)) return;

    const link = project.querySelector('.showcase-actions .btn-showcase[href]');
    if (link && link.href) {
      window.location.href = link.href;
    }
  });
});