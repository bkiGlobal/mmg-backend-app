(() => {
    const form = document.querySelector("#ledger-spreadsheet-form");
    if (!form) return;

    const body = form.querySelector("[data-form-rows]");
    const template = document.querySelector("#ledger-empty-row");
    const totalForms = form.querySelector("[name$='-TOTAL_FORMS']");
    const formatter = new Intl.NumberFormat("id-ID", {
        style: "currency",
        currency: "IDR",
        maximumFractionDigits: 0,
    });

    const visibleRows = () => (
        [...body.querySelectorAll("[data-form-row]")]
            .filter((row) => !row.hidden)
    );

    const isPopulated = (row) => (
        [...row.querySelectorAll("input, select, textarea")]
            .some((input) => {
                if (
                    input.type === "hidden"
                    || input.type === "checkbox"
                    || input.type === "file"
                    || input.name.endsWith("-date")
                ) return false;
                return String(input.value || "").trim() !== "";
            })
        || [...row.querySelectorAll("input[type='file']")]
            .some((input) => input.files && input.files.length)
    );

    const numberValue = (row, field) => {
        const input = row.querySelector(`[name$='-${field}']`);
        const parsed = Number.parseFloat(input?.value || "0");
        return Number.isFinite(parsed) ? parsed : 0;
    };

    const updateSummary = () => {
        const rows = visibleRows();
        const populated = rows.filter(isPopulated);
        const debit = rows.reduce(
            (total, row) => total + numberValue(row, "debet"),
            0,
        );
        const credit = rows.reduce(
            (total, row) => total + numberValue(row, "credit"),
            0,
        );
        form.querySelector("[data-row-count]").textContent = populated.length;
        form.querySelector("[data-debet-total]").textContent = formatter.format(debit);
        form.querySelector("[data-credit-total]").textContent = formatter.format(credit);
        form.querySelector("[data-net-total]").textContent = formatter.format(
            debit - credit,
        );
    };

    const renumberRows = () => {
        let number = 0;
        visibleRows().forEach((row) => {
            number += 1;
            const label = row.querySelector("[data-row-number]");
            if (label) label.textContent = number;
        });
    };

    const addRow = () => {
        const index = Number.parseInt(totalForms.value, 10);
        const html = template.innerHTML.replaceAll("__prefix__", String(index));
        body.insertAdjacentHTML("beforeend", html);
        totalForms.value = index + 1;
        renumberRows();
        updateSummary();
        const row = visibleRows().at(-1);
        row?.querySelector("select, input, textarea")?.focus();
        return row;
    };

    const deleteRow = (row) => {
        const deletion = row.querySelector("[name$='-DELETE']");
        if (deletion) deletion.value = "on";
        row.hidden = true;
        if (!visibleRows().length) addRow();
        renumberRows();
        updateSummary();
    };

    const setSelectValue = (select, value) => {
        const normalized = value.trim().toLocaleLowerCase("id");
        const option = [...select.options].find(
            (item) => (
                item.value === value
                || item.text.trim().toLocaleLowerCase("id") === normalized
            ),
        );
        if (option) select.value = option.value;
    };

    const pasteGrid = (event) => {
        const target = event.target.closest(".mmg-sheet-input");
        const text = event.clipboardData?.getData("text");
        if (!target || !text || (!text.includes("\t") && !text.includes("\n"))) {
            return;
        }
        event.preventDefault();
        const rows = text.replace(/\r/g, "").split("\n")
            .filter((line, index, values) => line || index < values.length - 1)
            .map((line) => line.split("\t"));
        const startRow = visibleRows().indexOf(target.closest("[data-form-row]"));
        const startCell = [...target.closest("tr").querySelectorAll(
            ".mmg-sheet-input:not([type='file'])",
        )].indexOf(target);

        rows.forEach((values, rowOffset) => {
            while (visibleRows().length <= startRow + rowOffset) addRow();
            const destinationRow = visibleRows()[startRow + rowOffset];
            const cells = [...destinationRow.querySelectorAll(
                ".mmg-sheet-input:not([type='file'])",
            )];
            values.forEach((value, columnOffset) => {
                const input = cells[startCell + columnOffset];
                if (!input) return;
                if (input.tagName === "SELECT") setSelectValue(input, value);
                else input.value = value.trim();
                input.dispatchEvent(new Event("input", { bubbles: true }));
            });
        });
        updateSummary();
    };

    form.addEventListener("click", (event) => {
        if (event.target.closest("[data-add-row]")) addRow();
        const deleteButton = event.target.closest("[data-delete-row]");
        if (deleteButton) deleteRow(deleteButton.closest("[data-form-row]"));

        if (event.target.closest("[data-apply-date]")) {
            const date = form.querySelector("[data-bulk-date]").value;
            visibleRows().forEach((row) => {
                const input = row.querySelector("[name$='-date']");
                if (input) input.value = date;
            });
        }

        if (event.target.closest("[data-fill-down]")) {
            const rows = visibleRows();
            if (!rows.length) return;
            const source = rows[0];
            ["project", "other", "date", "type", "payment_via"].forEach((field) => {
                const sourceInput = source.querySelector(`[name$='-${field}']`);
                if (!sourceInput) return;
                rows.slice(1).forEach((row) => {
                    const input = row.querySelector(`[name$='-${field}']`);
                    if (input && !input.value) input.value = sourceInput.value;
                });
            });
        }
    });

    form.addEventListener("input", updateSummary);
    form.addEventListener("change", updateSummary);
    form.addEventListener("paste", pasteGrid);
    form.addEventListener("keydown", (event) => {
        const target = event.target.closest(".mmg-sheet-input");
        if (!target || event.key !== "Enter" || target.tagName === "TEXTAREA") {
            return;
        }
        event.preventDefault();
        if (event.ctrlKey || event.metaKey) {
            addRow();
            return;
        }
        const row = target.closest("[data-form-row]");
        const rows = visibleRows();
        const rowIndex = rows.indexOf(row);
        const inputs = [...row.querySelectorAll(".mmg-sheet-input")];
        const columnIndex = inputs.indexOf(target);
        let nextRow = rows[rowIndex + 1];
        if (!nextRow) nextRow = addRow();
        const nextInputs = [...nextRow.querySelectorAll(".mmg-sheet-input")];
        nextInputs[columnIndex]?.focus();
    });

    renumberRows();
    updateSummary();
})();
