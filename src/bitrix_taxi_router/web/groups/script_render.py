GROUPS_PAGE_SCRIPT_RENDER = """    function setDistributionStatus(message, tone) {
      distributionStatus.hidden = false;
      distributionStatus.textContent = message;
      distributionStatus.classList.remove("is-error", "is-success");
      if (tone) {
        distributionStatus.classList.add(tone);
      }
    }

    function showDistributionLanding() {
      distributionGroupsPanel.hidden = false;
      distributionStatus.hidden = true;
      distributionForm.hidden = true;
    }

    function showDistributionForm() {
      distributionGroupsPanel.hidden = true;
      distributionStatus.hidden = false;
    }

    function setStatsStatus(message, tone) {
      statsStatus.hidden = false;
      statsStatus.textContent = message;
      statsStatus.classList.remove("is-error", "is-success");
      if (tone) {
        statsStatus.classList.add(tone);
      }
    }

    function createStatsItem(title, metaLines, pills) {
      const item = document.createElement("div");
      item.className = "reference-item";

      const itemTitle = document.createElement("div");
      itemTitle.className = "reference-item-title";
      itemTitle.textContent = title;
      item.appendChild(itemTitle);

      (metaLines || []).filter(Boolean).forEach((line) => {
        const meta = document.createElement("div");
        meta.className = "reference-item-meta";
        meta.textContent = line;
        item.appendChild(meta);
      });

      if (Array.isArray(pills) && pills.length) {
        const pillRow = document.createElement("div");
        pillRow.className = "reference-pill-row";
        pills.forEach((pill) => {
          const badge = document.createElement("span");
          badge.className = `reference-pill${pill.muted ? " is-muted" : ""}`;
          badge.textContent = pill.label;
          pillRow.appendChild(badge);
        });
        item.appendChild(pillRow);
      }

      return item;
    }

    function renderStatsEmpty(container, message) {
      container.innerHTML = "";
      const empty = document.createElement("div");
      empty.className = "stats-empty";
      empty.textContent = message;
      container.appendChild(empty);
    }

    function formatStatsDate(value) {
      if (!value) {
        return "нет данных";
      }
      const parsed = new Date(value);
      if (Number.isNaN(parsed.getTime())) {
        return value;
      }
      return parsed.toLocaleString("ru-RU");
    }

    function renderStatsData(payload) {
      const summary = payload && payload.summary ? payload.summary : {};
      const diagnostics = Array.isArray(payload && payload.diagnostics) ? payload.diagnostics : [];
      const journal = Array.isArray(payload && payload.journal) ? payload.journal : [];
      const members = Array.isArray(payload && payload.members) ? payload.members : [];

      statsSummaryList.innerHTML = "";
      statsSummaryList.appendChild(createStatsItem("Записей в журнале", [`Всего: ${summary.journal_count || 0}`], [
        { label: `Назначено: ${summary.assigned_count || 0}` },
        { label: `Ожидание: ${summary.waiting_count || 0}`, muted: true },
        { label: `Игнорировано: ${summary.ignored_count || 0}`, muted: true },
      ]));
      statsSummaryList.appendChild(createStatsItem("Runtime участников", [`Записей: ${summary.member_runtime_count || 0}`], []));
      statsSummaryList.appendChild(createStatsItem("Диагностических записей", [`Всего: ${summary.diagnostic_count || 0}`], []));

      if (!members.length) {
        renderStatsEmpty(statsMembersList, "Пока нет runtime-записей по участникам.");
      } else {
        statsMembersList.innerHTML = "";
        members.forEach((member) => {
          statsMembersList.appendChild(createStatsItem(
            member.user_name || `Пользователь ${member.user_id}`,
            [
              `ID: ${member.user_id}`,
              `Последняя сделка: ${member.last_assigned_deal_id || "не было"}`,
              `Последнее назначение: ${formatStatsDate(member.last_assigned_at)}`,
              `Обновлено: ${formatStatsDate(member.updated_at)}`,
            ],
            [],
          ));
        });
      }

      if (!diagnostics.length) {
        renderStatsEmpty(statsDiagnosticsList, "Диагностических записей пока нет.");
      } else {
        statsDiagnosticsList.innerHTML = "";
        diagnostics.forEach((item) => {
          const detailLines = [];
          if (item.deal_id) {
            detailLines.push(`Сделка: #${item.deal_id}`);
          }
          if (item.details && Object.keys(item.details).length) {
            detailLines.push(`Детали: ${JSON.stringify(item.details)}`);
          }
          detailLines.push(`Источник: ${item.source}`);
          detailLines.push(`Время: ${formatStatsDate(item.created_at)}`);
          statsDiagnosticsList.appendChild(createStatsItem(
            item.message || "Диагностическое событие",
            detailLines,
            [
              { label: item.level || "info", muted: item.level !== "error" },
            ],
          ));
        });
      }

      if (!journal.length) {
        renderStatsEmpty(statsJournalList, "Журнал пуст. Как только backend запишет обработку сделок, записи появятся здесь.");
      } else {
        statsJournalList.innerHTML = "";
        journal.forEach((item) => {
          const assignedTo = item.assigned_user_id
            ? `${item.assigned_user_name || item.assigned_user_id} (${item.assigned_user_id})`
            : "не назначено";
          statsJournalList.appendChild(createStatsItem(
            `Сделка #${item.deal_id}`,
            [
              `Статус: ${item.status}`,
              `Назначено: ${assignedTo}`,
              `Поле: ${item.assigned_field_id || "не заполнялось"}`,
              `Комментарий: ${item.note || "нет"}`,
              `Обновлено: ${formatStatsDate(item.updated_at)}`,
            ],
            [
              { label: item.event_type || "event" },
            ],
          ));
        });
      }
    }

    function createDefaultDistributionConfig(referenceData) {
      const defaultResponsibleField = (referenceData.responsible_fields || []).find((field) => field.is_default)
        || (referenceData.responsible_fields || [])[0]
        || null;
      return {
        name: "",
        distribution_type: "round_robin_load_time",
        event_type: "deal_created",
        distribution_stage_id: "",
        responsible_field_id: defaultResponsibleField ? defaultResponsibleField.id : "",
        wait_seconds: "",
        retry_interval_seconds: "",
        is_active: true,
        members: [],
        load_stage_ids: [],
      };
    }

    function normalizeLoadedDistributionConfig(config, referenceData) {
      const defaults = createDefaultDistributionConfig(referenceData);
      if (!config) {
        return defaults;
      }

      const members = Array.isArray(config.members) ? config.members : [];
      const loadStageIds = Array.isArray(config.load_stage_ids) ? config.load_stage_ids : [];

      return {
        ...defaults,
        ...config,
        members,
        load_stage_ids: loadStageIds,
      };
    }

    function renderSelectOptions(selectElement, items, selectedValue, placeholder) {
      selectElement.innerHTML = "";

      if (placeholder) {
        const placeholderOption = document.createElement("option");
        placeholderOption.value = "";
        placeholderOption.textContent = placeholder;
        selectElement.appendChild(placeholderOption);
      }

      (items || []).forEach((item) => {
        const option = document.createElement("option");
        option.value = item.id;
        option.textContent = item.name || item.id;
        option.selected = item.id === selectedValue;
        selectElement.appendChild(option);
      });
    }

    function renderParticipants(config, users) {
      participantsList.innerHTML = "";
      const selectedMembers = new Map((config.members || []).map((member) => [member.user_id, member]));

      (users || []).forEach((user) => {
        const selectedMember = selectedMembers.get(user.id);
        const row = document.createElement("div");
        row.className = "participant-row";

        const label = document.createElement("label");
        label.className = "participant-main";

        const checkbox = document.createElement("input");
        checkbox.type = "checkbox";
        checkbox.checked = Boolean(selectedMember);
        checkbox.dataset.userId = user.id;

        const info = document.createElement("span");
        info.className = "participant-info";

        const name = document.createElement("span");
        name.className = "participant-name";
        name.textContent = user.name || `Пользователь ${user.id}`;

        const meta = document.createElement("span");
        meta.className = "participant-meta";
        meta.textContent = `ID: ${user.id}${user.is_active ? " · активен" : " · неактивен"}`;

        info.append(name, meta);
        label.append(checkbox, info);

        const limitWrapper = document.createElement("label");
        limitWrapper.className = "participant-limit";

        const limitLabel = document.createElement("span");
        limitLabel.className = "participant-limit-label";
        limitLabel.textContent = "Лимит";

        const limitInput = document.createElement("input");
        limitInput.className = "distribution-input";
        limitInput.type = "number";
        limitInput.min = "0";
        limitInput.step = "1";
        limitInput.placeholder = "0";
        limitInput.value = selectedMember ? String(selectedMember.limit) : "";
        limitInput.dataset.limitFor = user.id;
        limitInput.disabled = !checkbox.checked;

        checkbox.addEventListener("change", () => {
          limitInput.disabled = !checkbox.checked;
          if (!checkbox.checked) {
            limitInput.value = "";
          }
        });

        limitWrapper.append(limitLabel, limitInput);
        row.append(label, limitWrapper);
        participantsList.appendChild(row);
      });
    }

    function renderLoadStages(config, stages) {
      loadStagesList.innerHTML = "";
      const selectedStageIds = new Set(config.load_stage_ids || []);

      (stages || []).forEach((stage) => {
        const row = document.createElement("label");
        row.className = "checkbox-row";

        const main = document.createElement("span");
        main.className = "checkbox-main";

        const checkbox = document.createElement("input");
        checkbox.type = "checkbox";
        checkbox.checked = selectedStageIds.has(stage.id);
        checkbox.dataset.stageId = stage.id;

        const info = document.createElement("span");
        info.className = "checkbox-info";

        const name = document.createElement("span");
        name.className = "checkbox-name";
        name.textContent = stage.name || stage.id;

        const meta = document.createElement("span");
        meta.className = "checkbox-meta";
        meta.textContent = `ID: ${stage.id}${stage.sort !== undefined ? ` · sort: ${stage.sort}` : ""}`;

        info.append(name, meta);
        main.append(checkbox, info);
        row.appendChild(main);
        loadStagesList.appendChild(row);
      });
    }

    function renderDistributionConfigForm() {
      const referenceData = distributionState.referenceData || { users: [], stages: [], responsible_fields: [] };
      const config = distributionState.config || createDefaultDistributionConfig(referenceData);

      groupNameInput.value = config.name || "";
      distributionTypeSelect.value = config.distribution_type || "round_robin_load_time";
      eventTypeSelect.value = config.event_type || "deal_created";
      waitSecondsInput.value = config.wait_seconds === "" ? "" : String(config.wait_seconds ?? "");
      retryIntervalInput.value = config.retry_interval_seconds === "" ? "" : String(config.retry_interval_seconds ?? "");
      groupActiveInput.checked = Boolean(config.is_active);

      renderSelectOptions(distributionStageSelect, referenceData.stages, config.distribution_stage_id, "Выберите статус");
      renderSelectOptions(
        responsibleFieldSelect,
        referenceData.responsible_fields,
        config.responsible_field_id,
        "Выберите поле",
      );
      renderParticipants(config, referenceData.users);
      renderLoadStages(config, referenceData.stages);
      showDistributionForm();
      distributionForm.hidden = false;
    }

    function collectDistributionConfigFromForm() {
      const members = [];
      participantsList.querySelectorAll("[data-user-id]").forEach((checkbox) => {
        if (!checkbox.checked) {
          return;
        }

        const limitInput = participantsList.querySelector(`[data-limit-for="${checkbox.dataset.userId}"]`);
        members.push({
          user_id: checkbox.dataset.userId,
          limit: limitInput ? Number(limitInput.value || 0) : 0,
        });
      });

      const loadStageIds = [];
      loadStagesList.querySelectorAll("[data-stage-id]").forEach((checkbox) => {
        if (checkbox.checked) {
          loadStageIds.push(checkbox.dataset.stageId);
        }
      });

      return {
        name: groupNameInput.value.trim(),
        distribution_type: distributionTypeSelect.value,
        event_type: eventTypeSelect.value,
        distribution_stage_id: distributionStageSelect.value,
        responsible_field_id: responsibleFieldSelect.value,
        wait_seconds: Number(waitSecondsInput.value || 0),
        retry_interval_seconds: Number(retryIntervalInput.value || 0),
        is_active: groupActiveInput.checked,
        members,
        load_stage_ids: loadStageIds,
      };
    }

    function applyBulkLimitFromForm() {
      const bulkValue = bulkLimitValueInput.value.trim();
      if (!bulkValue) {
        setDistributionStatus("Укажите значение лимита для массового заполнения.", "is-error");
        return;
      }

      const shouldApplyToAll = bulkLimitScopeSelect.value === "all";
      participantsList.querySelectorAll("[data-user-id]").forEach((checkbox) => {
        if (!shouldApplyToAll && !checkbox.checked) {
          return;
        }

        const limitInput = participantsList.querySelector(`[data-limit-for="${checkbox.dataset.userId}"]`);
        if (!limitInput) {
          return;
        }
        if (!checkbox.checked && shouldApplyToAll) {
          checkbox.checked = true;
          limitInput.disabled = false;
        }
        limitInput.value = bulkValue;
      });

      setDistributionStatus("Лимиты обновлены в форме. Чтобы сохранить группу, нажмите «Применить».", "is-success");
    }

    function setActiveView(view) {
      const content = sectionContent[view] || sectionContent.overview;
      const isDistribution = view === "distribution";
      const isStats = view === "stats";

      defaultPanel.hidden = isDistribution || isStats;
      statsPanel.hidden = !isStats;
      distributionPanel.hidden = !isDistribution;
      mainCard.classList.remove("is-centered");

      if (!isDistribution && !isStats) {
        distributionState.openFormRequested = false;
        sectionBadge.textContent = content.badge;
        sectionTitle.textContent = content.title;
        sectionDescription.textContent = content.description;
      } else if (isDistribution) {
        distributionState.openFormRequested = false;
        showDistributionLanding();
        loadDistributionReferenceData();
      } else {
        loadStatsData(false);
      }

      menuButtons.forEach((button) => {
        button.classList.toggle("is-active", button.dataset.view === view);
      });
    }
"""
