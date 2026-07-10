// Modal — open/close + YouTube playback stop on close

(function () {
  const VIDEO_SRC =
    "https://www.youtube.com/embed/dQw4w9WgXcQ?autoplay=1&rel=0";

  function openModal(modal) {
    const iframe = modal.querySelector("iframe");
    if (iframe && !iframe.src) {
      iframe.src = VIDEO_SRC;
    }
    modal.classList.add("is-open");
    modal.setAttribute("aria-hidden", "false");
    document.body.style.overflow = "hidden";
  }

  function closeModal(modal) {
    const iframe = modal.querySelector("iframe");
    if (iframe) {
      // Clearing src fully stops playback (pausing alone leaves audio running
      // on some browsers, and YouTube's iframe API requires an extra script).
      iframe.src = "";
    }
    modal.classList.remove("is-open");
    modal.setAttribute("aria-hidden", "true");
    document.body.style.overflow = "";
  }

  document.addEventListener("click", function (event) {
    const trigger = event.target.closest("[data-open-modal]");
    if (trigger) {
      event.preventDefault();
      const target = document.querySelector(trigger.dataset.openModal);
      if (target) openModal(target);
      return;
    }

    const closer = event.target.closest("[data-close-modal]");
    if (closer) {
      event.preventDefault();
      const modal = closer.closest(".modal");
      if (modal) closeModal(modal);
      return;
    }

    // Click outside the panel closes the modal
    const openModalEl = event.target.closest(".modal.is-open");
    if (!openModalEl && document.querySelector(".modal.is-open")) {
      // event.target is the overlay itself
      const overlay = event.target;
      if (overlay && overlay.classList && overlay.classList.contains("modal")) {
        closeModal(overlay);
      }
    }
  });

  document.addEventListener("keydown", function (event) {
    if (event.key === "Escape") {
      const open = document.querySelector(".modal.is-open");
      if (open) closeModal(open);
    }
  });
})();
