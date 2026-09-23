document.addEventListener("DOMContentLoaded", () => {
  const root = document.documentElement;
  const savedTheme = localStorage.getItem("nursing-theme") || "light";
  root.dataset.theme = savedTheme;
  const themeToggleButtons = document.querySelectorAll(".theme-toggle-btn");
  const setThemeIcon = () => {
    const icon = root.dataset.theme === "dark" ? "☀" : "☾";
    themeToggleButtons.forEach((btn) => {
      const iconEl = btn.querySelector(".liquid-nav-icon");
      if (iconEl) iconEl.textContent = icon;
      else btn.textContent = icon;
    });
  };
  setThemeIcon();
  themeToggleButtons.forEach((btn) => {
    btn.addEventListener("click", () => {
      root.dataset.theme = root.dataset.theme === "dark" ? "light" : "dark";
      localStorage.setItem("nursing-theme", root.dataset.theme);
      setThemeIcon();
    });
  });

  const sidebar = document.getElementById("sidebar"),
    overlay = document.getElementById("sidebarOverlay");
  const toggleSidebar = () => {
    sidebar?.classList.toggle("open");
    overlay?.classList.toggle("show");
  };
  document
    .getElementById("menuToggle")
    ?.addEventListener("click", toggleSidebar);
  document
    .getElementById("sidebarClose")
    ?.addEventListener("click", toggleSidebar);
  overlay?.addEventListener("click", toggleSidebar);

  // ===== MOBILE QUICK DRAWER (Profil, Kelola Perawat, Ganti Tema, Keluar) =====
  const quickDrawer = document.getElementById("mobileQuickDrawer"),
    quickOverlay = document.getElementById("mobileQuickOverlay");
  const toggleQuickDrawer = () => {
    quickDrawer?.classList.toggle("open");
    quickOverlay?.classList.toggle("show");
  };
  document
    .getElementById("mobileQuickToggle")
    ?.addEventListener("click", toggleQuickDrawer);
  document
    .getElementById("mobileQuickClose")
    ?.addEventListener("click", toggleQuickDrawer);
  quickOverlay?.addEventListener("click", toggleQuickDrawer);

  const currentPath = window.location.pathname;
  document.querySelectorAll(".nav-item").forEach((link) => {
    const path = new URL(link.href).pathname;
    if (path === currentPath || (path !== "/" && currentPath.startsWith(path)))
      link.classList.add("active");
  });

  // ===== LIQUID BOTTOM NAV (mobile) =====
  const liquidItems = Array.from(document.querySelectorAll(".liquid-nav-item"));
  const blobMain = document.getElementById("liquidBlobMain");

  const moveLiquidBlob = (el, instant = false) => {
    if (!el || !blobMain) return;
    const shell = el.closest(".liquid-navbar-inner");
    if (!shell) return;
    const shellRect = shell.getBoundingClientRect();
    const itemRect = el.getBoundingClientRect();
    const center = itemRect.left - shellRect.left + itemRect.width / 2;
    const mainLeft = center - 25; // half of 50px blob

    if (instant) {
      const prevMain = blobMain.style.transition;
      blobMain.style.transition = "none";
      blobMain.style.left = `${mainLeft}px`;
      // force reflow before restoring transitions
      void blobMain.offsetWidth;
      blobMain.style.transition = prevMain;
    } else {
      blobMain.style.left = `${mainLeft}px`;
    }
  };

  const activeLiquidItem = () =>
    liquidItems.find((el) => el.classList.contains("active"));

  // ===== GARIS EKG YANG MENYAPU KE TAB AKTIF =====
  const ekgSvg = document.getElementById("liquidEkg");
  const ekgPath = document.getElementById("liquidEkgPath");

  const buildEkgPath = (centerX, width, height) => {
    const baseY = height / 2;
    const up = height * 0.42; // tinggi lonjakan ke atas
    const down = height * 0.32; // dalam lekukan ke bawah

    return [
      `M0,${baseY}`,
      `L${centerX - 16},${baseY}`,
      `L${centerX - 8},${baseY - 3}`,
      `L${centerX - 3},${baseY + down}`,
      `L${centerX + 2},${baseY - up}`,
      `L${centerX + 7},${baseY + 6}`,
      `L${centerX + 14},${baseY}`,
      `L${width},${baseY}`,
    ].join(" ");
  };

  const sweepEkg = (el) => {
    if (!el || !ekgPath || !ekgSvg) return;
    const shell = el.closest(".liquid-navbar-inner");
    if (!shell) return;

    const shellRect = shell.getBoundingClientRect();
    const itemRect = el.getBoundingClientRect();
    const centerX = itemRect.left - shellRect.left + itemRect.width / 2;

    ekgSvg.setAttribute("viewBox", `0 0 ${shellRect.width} ${shellRect.height}`);
    ekgPath.setAttribute(
      "d",
      buildEkgPath(centerX, shellRect.width, shellRect.height)
    );

    const length = ekgPath.getTotalLength();
    ekgPath.style.strokeDasharray = `${length}`;
    ekgPath.style.strokeDashoffset = `${length}`;
    ekgPath.style.opacity = "1";

    // paksa reflow supaya animasi selalu dimulai ulang dari awal
    void ekgPath.getBoundingClientRect();

    ekgPath.animate(
      [
        { strokeDashoffset: length, opacity: 1 },
        { strokeDashoffset: 0, opacity: 1, offset: 0.8 },
        { strokeDashoffset: 0, opacity: 0 },
      ],
      { duration: 700, easing: "ease-out", fill: "forwards" }
    );
  };

  const initialActive = activeLiquidItem();
  if (initialActive) {
    // wait a frame so layout (fonts/icons) is settled before measuring
    requestAnimationFrame(() => {
      moveLiquidBlob(initialActive, true);
      sweepEkg(initialActive);
    });
  }

  liquidItems.forEach((el) => {
    if (el.tagName === "A") {
      el.addEventListener("click", () => {
        liquidItems.forEach((i) => i.classList.remove("active"));
        el.classList.add("active");
        moveLiquidBlob(el);
        sweepEkg(el);
      });
    }
  });

  let liquidResizeTimer;
  window.addEventListener("resize", () => {
    clearTimeout(liquidResizeTimer);
    liquidResizeTimer = setTimeout(() => {
      const current = activeLiquidItem();
      if (current) {
        moveLiquidBlob(current, true);
        if (ekgPath) ekgPath.style.opacity = "0"; // sembunyikan, tak perlu sweep ulang saat resize
      }
    }, 120);
  });

  const revealObserver = new IntersectionObserver(
    (entries) =>
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          entry.target.classList.add("show");
          revealObserver.unobserve(entry.target);
        }
      }),
    { threshold: 0.08 }
  );
  document
    .querySelectorAll(".reveal")
    .forEach((el) => revealObserver.observe(el));

  const animateNumber = (el, target, decimals = 0) => {
    const duration = 1100,
      start = performance.now();
    const tick = (now) => {
      const p = Math.min((now - start) / duration, 1),
        eased = 1 - Math.pow(1 - p, 3),
        value = target * eased;
      el.textContent = decimals ? value.toFixed(decimals) : Math.floor(value);
      if (p < 1) requestAnimationFrame(tick);
      else el.textContent = decimals ? target.toFixed(decimals) : target;
    };
    requestAnimationFrame(tick);
  };
  document
    .querySelectorAll("[data-counter]")
    .forEach((el) => animateNumber(el, Number(el.dataset.counter)));
  document
    .querySelectorAll("[data-counter-decimal]")
    .forEach((el) => animateNumber(el, Number(el.dataset.counterDecimal), 1));
  document
    .querySelectorAll(".progress-bar[data-progress]")
    .forEach((bar) =>
      setTimeout(
        () =>
          (bar.style.width = `${Math.min(Number(bar.dataset.progress), 100)}%`),
        220
      )
    );

  document.querySelectorAll(".btn").forEach((button) =>
    button.addEventListener("click", function (e) {
      const circle = document.createElement("span"),
        d = Math.max(this.clientWidth, this.clientHeight),
        r = this.getBoundingClientRect();
      circle.className = "ripple";
      circle.style.width = circle.style.height = `${d}px`;
      circle.style.left = `${e.clientX - r.left - d / 2}px`;
      circle.style.top = `${e.clientY - r.top - d / 2}px`;
      this.querySelector(".ripple")?.remove();
      this.appendChild(circle);
    })
  );

  // Password show/hide toggle (eye icon)
  document.querySelectorAll(".toggle-password").forEach((btn) => {
    btn.addEventListener("click", () => {
      const input = btn.closest(".password-field")?.querySelector("input");
      if (!input) return;
      const showing = btn.classList.toggle("is-visible");
      input.type = showing ? "text" : "password";
      btn.setAttribute(
        "aria-label",
        showing ? "Sembunyikan password" : "Tampilkan password"
      );
    });
  });

  // Row action menu (kebab / titik-tiga) di tabel admin: buka/tutup,
  // tutup otomatis kalau klik di luar atau ada menu lain yang dibuka.
  const rowMenus = document.querySelectorAll(".row-menu");
  const closeAllRowMenus = (except) => {
    rowMenus.forEach((menu) => {
      if (menu !== except) {
        menu.classList.remove("open");
        menu.querySelector(".row-menu-btn")?.setAttribute("aria-expanded", "false");
      }
    });
  };
  rowMenus.forEach((menu) => {
    const btn = menu.querySelector(".row-menu-btn");
    btn?.addEventListener("click", (e) => {
      e.stopPropagation();
      const willOpen = !menu.classList.contains("open");
      closeAllRowMenus();
      menu.classList.toggle("open", willOpen);
      btn.setAttribute("aria-expanded", willOpen ? "true" : "false");
    });
  });
  document.addEventListener("click", () => closeAllRowMenus());
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") closeAllRowMenus();
  });

  document.querySelectorAll(".flash").forEach((flash) => {
    flash
      .querySelector(".flash-close")
      ?.addEventListener("click", () => flash.remove());
    setTimeout(() => {
      flash.classList.add("hide");
      setTimeout(() => flash.remove(), 450);
    }, 5000);
  });

  // Realtime table search. Every table gets a compact search bar automatically.
  document.querySelectorAll(".table").forEach((table) => {
    if (table.closest(".table-wrapper") || table.dataset.noSearch === "true")
      return;
    const wrapper = document.createElement("div");
    wrapper.className = "table-wrapper";
    const parent = table.parentNode;
    parent.insertBefore(wrapper, table);
    wrapper.appendChild(table);
    const toolbar = document.createElement("div");
    toolbar.className = "table-toolbar";
    toolbar.innerHTML = `<div><strong>Data</strong><span class="result-count"></span></div><label class="table-search">⌕<input type="search" placeholder="Cari data..." aria-label="Cari data"></label>`;
    wrapper.parentNode.insertBefore(toolbar, wrapper);
    toolbar.dataset.tableFor = "1";
    const input = toolbar.querySelector("input"),
      rows = [...table.querySelectorAll("tbody tr")],
      count = toolbar.querySelector(".result-count");
    const filter = () => {
      const q = input.value.toLowerCase().trim();
      let shown = 0;
      rows.forEach((row) => {
        const match = row.textContent.toLowerCase().includes(q);
        row.style.display = match ? "" : "none";
        if (match) shown++;
      });
      count.textContent = ` · ${shown} hasil`;
    };
    filter();
    input.addEventListener("input", filter);
  });

  // Logbook detail modal
  const modal = document.getElementById("detailModal"),
    body = document.getElementById("modalBody"),
    title = document.getElementById("modalTitle");
  const closeModal = () => {
    modal?.classList.remove("show");
    modal?.setAttribute("aria-hidden", "true");
  };
  document.querySelectorAll("[data-logbook-modal]").forEach((btn) =>
    btn.addEventListener("click", () => {
      title.textContent = btn.dataset.title || "Detail Keterampilan";
      body.innerHTML = `<div class="modal-detail-grid"><div><span>Kompetensi</span><strong>${
        btn.dataset.competency || "-"
      }</strong></div><div><span>Target</span><strong>${
        btn.dataset.target || "-"
      }</strong></div><div><span>Progress</span><strong>${
        btn.dataset.progress || "0"
      }</strong></div><div><span>Status</span><strong>${
        btn.dataset.status || "Belum selesai"
      }</strong></div></div><div class="modal-actions"><a class="btn btn-primary" href="${
        btn.dataset.url
      }">Buka Detail Lengkap</a></div>`;
      modal.classList.add("show");
      modal.setAttribute("aria-hidden", "false");
    })
  );
  document
    .querySelectorAll("[data-close-modal]")
    .forEach((btn) => btn.addEventListener("click", closeModal));
  modal?.addEventListener("click", (e) => {
    if (e.target === modal) closeModal();
  });
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") closeModal();
  });

  // Confirm modal — pengganti confirm() bawaan browser supaya tidak
  // muncul dialog default ("localhost menyatakan...") saat melakukan aksi.
  const confirmModal = document.getElementById("confirmModal"),
    confirmMessage = document.getElementById("confirmModalMessage"),
    confirmOkBtn = document.getElementById("confirmModalOk");
  let pendingConfirmForm = null;
  const closeConfirmModal = () => {
    confirmModal?.classList.remove("show");
    confirmModal?.setAttribute("aria-hidden", "true");
    pendingConfirmForm = null;
  };
  document.querySelectorAll("form[data-confirm]").forEach((form) => {
    form.addEventListener("submit", (e) => {
      if (form.dataset.confirmed === "true") return;
      e.preventDefault();
      pendingConfirmForm = form;
      confirmMessage.textContent = form.dataset.confirm;
      confirmModal.classList.add("show");
      confirmModal.setAttribute("aria-hidden", "false");
    });
  });
  confirmOkBtn?.addEventListener("click", () => {
    if (pendingConfirmForm) {
      pendingConfirmForm.dataset.confirmed = "true";
      if (pendingConfirmForm.requestSubmit) {
        pendingConfirmForm.requestSubmit();
      } else {
        pendingConfirmForm.submit();
      }
    }
    closeConfirmModal();
  });
  document
    .querySelectorAll("[data-confirm-cancel]")
    .forEach((btn) => btn.addEventListener("click", closeConfirmModal));
  confirmModal?.addEventListener("click", (e) => {
    if (e.target === confirmModal) closeConfirmModal();
  });
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") closeConfirmModal();
  });

  // ============================================================
  // LIVE CLOCK — jam & tanggal berjalan di topbar
  // ============================================================
  const clockTime = document.querySelector("#clockWidget .clock-time");
  const clockDate = document.querySelector("#clockWidget .clock-date");
  const hariList = [
    "Minggu",
    "Senin",
    "Selasa",
    "Rabu",
    "Kamis",
    "Jumat",
    "Sabtu",
  ];
  const bulanList = [
    "Januari",
    "Februari",
    "Maret",
    "April",
    "Mei",
    "Juni",
    "Juli",
    "Agustus",
    "September",
    "Oktober",
    "November",
    "Desember",
  ];
  const tickClock = () => {
    if (!clockTime) return;
    const now = new Date();
    clockTime.textContent = now.toLocaleTimeString("id-ID", {
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
    });
    clockDate.textContent = `${hariList[now.getDay()]}, ${now.getDate()} ${
      bulanList[now.getMonth()]
    }`;
  };
  tickClock();
  setInterval(tickClock, 1000);

  // ============================================================
  // TYPING EFFECT — sapaan "Halo, {nama}" diketik hidup
  // ============================================================
  document.querySelectorAll("[data-typing]").forEach((el) => {
    const full = el.textContent.trim();
    el.textContent = "";
    const caret = document.createElement("span");
    caret.className = "type-caret";
    el.after(caret);
    let i = 0;
    const type = () => {
      if (i <= full.length) {
        el.textContent = full.slice(0, i);
        i++;
        setTimeout(type, 38);
      } else {
        setTimeout(() => caret.remove(), 1200);
      }
    };
    type();
  });

  // ============================================================
  // CARD TILT — efek 3D mengikuti kursor pada .card
  // ============================================================
  if (
    !window.matchMedia("(prefers-reduced-motion: reduce)").matches &&
    window.matchMedia("(pointer: fine)").matches
  ) {
    document.querySelectorAll(".card").forEach((card) => {
      card.classList.add("tilt");
      const glow = document.createElement("div");
      glow.className = "tilt-glow";
      card.appendChild(glow);
      card.addEventListener("mousemove", (e) => {
        const r = card.getBoundingClientRect();
        const x = e.clientX - r.left,
          y = e.clientY - r.top;
        const rx = (y / r.height - 0.5) * -6,
          ry = (x / r.width - 0.5) * 6;
        card.style.transform = `perspective(900px) rotateX(${rx}deg) rotateY(${ry}deg) translateY(-3px)`;
        card.style.setProperty("--mx", `${(x / r.width) * 100}%`);
        card.style.setProperty("--my", `${(y / r.height) * 100}%`);
      });
      card.addEventListener("mouseleave", () => {
        card.style.transform = "";
      });
    });
  }

  // ============================================================
  // AMBIENT PARTICLE NETWORK — kanvas latar hidup bertema Eka Hospital
  // (titik merah & hijau melayang, saling terhubung — nuansa "monitor" rumah sakit)
  // ============================================================
  (() => {
    const canvas = document.getElementById("particleCanvas");
    if (
      !canvas ||
      window.matchMedia("(prefers-reduced-motion: reduce)").matches
    )
      return;
    const ctx = canvas.getContext("2d");
    let w,
      h,
      particles,
      dpr = Math.min(window.devicePixelRatio || 1, 2);
    const COLORS = ["#a12135", "#1b9346", "#8dc63f"];
    const COUNT = window.innerWidth < 780 ? 26 : 55;

    const resize = () => {
      w = canvas.width = window.innerWidth * dpr;
      h = canvas.height = window.innerHeight * dpr;
      canvas.style.width = window.innerWidth + "px";
      canvas.style.height = window.innerHeight + "px";
    };
    const makeParticles = () => {
      particles = Array.from({ length: COUNT }, () => ({
        x: Math.random() * w,
        y: Math.random() * h,
        vx: (Math.random() - 0.5) * 0.35 * dpr,
        vy: (Math.random() - 0.5) * 0.35 * dpr,
        r: (Math.random() * 1.6 + 1) * dpr,
        c: COLORS[Math.floor(Math.random() * COLORS.length)],
      }));
    };
    resize();
    makeParticles();
    window.addEventListener("resize", () => {
      resize();
      makeParticles();
    });

    const LINK_DIST = 130 * dpr;
    let raf;
    const draw = () => {
      ctx.clearRect(0, 0, w, h);
      for (const p of particles) {
        p.x += p.vx;
        p.y += p.vy;
        if (p.x < 0 || p.x > w) p.vx *= -1;
        if (p.y < 0 || p.y > h) p.vy *= -1;
        ctx.beginPath();
        ctx.arc(p.x, p.y, p.r, 0, Math.PI * 2);
        ctx.fillStyle = p.c;
        ctx.fill();
      }
      for (let i = 0; i < particles.length; i++) {
        for (let j = i + 1; j < particles.length; j++) {
          const a = particles[i],
            b = particles[j];
          const dx = a.x - b.x,
            dy = a.y - b.y,
            dist = Math.hypot(dx, dy);
          if (dist < LINK_DIST) {
            ctx.strokeStyle = `rgba(120,130,120,${
              (1 - dist / LINK_DIST) * 0.18
            })`;
            ctx.lineWidth = 1;
            ctx.beginPath();
            ctx.moveTo(a.x, a.y);
            ctx.lineTo(b.x, b.y);
            ctx.stroke();
          }
        }
      }
      raf = requestAnimationFrame(draw);
    };
    draw();
    document.addEventListener("visibilitychange", () => {
      if (document.hidden) cancelAnimationFrame(raf);
      else draw();
    });
  })();

  // ============================================================
  // CONFETTI — meletup saat progress level mencapai 100%
  // ============================================================
  const fireConfetti = () => {
    const canvas = document.getElementById("confettiCanvas");
    if (!canvas) return;
    const ctx = canvas.getContext("2d");
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    canvas.width = window.innerWidth * dpr;
    canvas.height = window.innerHeight * dpr;
    canvas.style.width = "100%";
    canvas.style.height = "100%";
    const COLORS = ["#a12135", "#1b9346", "#8dc63f", "#f4a62a", "#ffffff"];
    const pieces = Array.from({ length: 130 }, () => ({
      x: Math.random() * canvas.width,
      y: -20 * dpr,
      vx: (Math.random() - 0.5) * 4 * dpr,
      vy: (Math.random() * 3 + 2) * dpr,
      size: (Math.random() * 6 + 4) * dpr,
      rot: Math.random() * 360,
      vr: (Math.random() - 0.5) * 12,
      c: COLORS[Math.floor(Math.random() * COLORS.length)],
    }));
    let frame = 0;
    const loop = () => {
      frame++;
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      let alive = false;
      pieces.forEach((p) => {
        p.x += p.vx;
        p.y += p.vy;
        p.vy += 0.06 * dpr;
        p.rot += p.vr;
        if (p.y < canvas.height + 30) alive = true;
        ctx.save();
        ctx.translate(p.x, p.y);
        ctx.rotate((p.rot * Math.PI) / 180);
        ctx.fillStyle = p.c;
        ctx.fillRect(-p.size / 2, -p.size / 2, p.size, p.size * 0.6);
        ctx.restore();
      });
      if (alive && frame < 260) requestAnimationFrame(loop);
      else ctx.clearRect(0, 0, canvas.width, canvas.height);
    };
    loop();
  };
  document.querySelectorAll(".progress-bar[data-progress]").forEach((bar) => {
    if (Number(bar.dataset.progress) >= 100) setTimeout(fireConfetti, 900);
  });
});
