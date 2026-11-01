document.addEventListener("DOMContentLoaded", () => {
  const addForms = document.querySelectorAll(".add-to-cart-form");

  addForms.forEach((form) => {
    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      const button = form.querySelector("button");
      const status = form.querySelector(".form-status");
      button.disabled = true;

      try {
        const response = await fetch(form.action, {
          method: "POST",
          headers: { "X-Requested-With": "XMLHttpRequest" },
        });
        if (!response.ok) throw new Error("Could not add this product.");
        const result = await response.json();
        document.querySelectorAll("[data-cart-count]").forEach((count) => {
          count.textContent = result.cart_count;
        });
        status.textContent = "Added";
        window.setTimeout(() => { status.textContent = ""; }, 1800);
      } catch (error) {
        status.textContent = "Please try again";
      } finally {
        button.disabled = false;
      }
    });
  });
});