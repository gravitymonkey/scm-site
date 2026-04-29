(() => {
  const triggers = Array.from(document.querySelectorAll("[data-annotation-trigger]"));
  if (!triggers.length) {
    return;
  }

  let openTrigger = null;

  function closeCurrent() {
    if (!openTrigger) {
      return;
    }
    const popover = document.getElementById(openTrigger.getAttribute("aria-controls"));
    openTrigger.setAttribute("aria-expanded", "false");
    openTrigger.parentElement?.removeAttribute("data-open");
    if (popover) {
      popover.hidden = true;
    }
    openTrigger = null;
  }

  function openFor(trigger) {
    if (openTrigger && openTrigger !== trigger) {
      closeCurrent();
    }

    const popover = document.getElementById(trigger.getAttribute("aria-controls"));
    if (!popover) {
      return;
    }

    trigger.setAttribute("aria-expanded", "true");
    trigger.parentElement?.setAttribute("data-open", "true");
    popover.hidden = false;
    openTrigger = trigger;
  }

  for (const trigger of triggers) {
    trigger.addEventListener("click", (event) => {
      event.preventDefault();
      if (openTrigger === trigger) {
        closeCurrent();
        return;
      }
      openFor(trigger);
    });
  }

  document.addEventListener("click", (event) => {
    if (!openTrigger) {
      return;
    }
    if (openTrigger.parentElement?.contains(event.target)) {
      return;
    }
    closeCurrent();
  });

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
      if (!openTrigger) {
        return;
      }
      const trigger = openTrigger;
      closeCurrent();
      trigger.focus();
    }
  });
})();
