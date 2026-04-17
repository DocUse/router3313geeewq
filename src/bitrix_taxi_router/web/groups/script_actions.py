GROUPS_PAGE_SCRIPT_ACTIONS = """    async function saveDistributionConfig() {
      const distributionMemberId = await resolveDistributionMemberId();
      if (!distributionMemberId) {
        setDistributionStatus("Не удалось определить member_id портала для сохранения.", "is-error");
        return;
      }

      setDistributionStatus("Сохраняем конфигурацию группы распределения...");

      try {
        const payload = collectDistributionConfigFromForm();
        const response = await fetchJson(
          `/api/ui/groups/config?member_id=${encodeURIComponent(distributionMemberId)}`,
          {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
            },
            body: JSON.stringify(payload),
          },
        );

        distributionState.config = normalizeLoadedDistributionConfig(response.config, distributionState.referenceData);
        statsState.isLoaded = false;
        renderDistributionConfigForm();
        setDistributionStatus("Группа распределения сохранена. После перезагрузки конфигурация будет поднята из базы.", "is-success");
      } catch (error) {
        setDistributionStatus(error.message || "Не удалось сохранить конфигурацию группы.", "is-error");
      }
    }

    async function runEventDeliveryCheck() {
      const distributionMemberId = await resolveDistributionMemberId();
      if (!distributionMemberId) {
        setStatsStatus("Не удалось определить member_id портала для запуска self-test.", "is-error");
        return;
      }

      setStatsStatus("Запускаем self-test доставки события из Bitrix...");
      try {
        const payload = await fetchJson(
          `/api/ui/stats/event-delivery-check?member_id=${encodeURIComponent(distributionMemberId)}`,
          { method: "POST" },
        );
        statsState.isLoaded = false;
        setStatsStatus(
          `Self-test отправлен. check_id: ${payload.check_id}. Через пару секунд журнал обновится автоматически.`,
          "is-success",
        );
        window.setTimeout(() => {
          loadStatsData(true);
        }, 2500);
      } catch (error) {
        setStatsStatus(error.message || "Не удалось запустить self-test доставки события.", "is-error");
      }
    }

    function handleCreateDistributionGroupClick() {
      distributionState.openFormRequested = true;
      loadDistributionReferenceData();
    }

    applyBulkLimitButton.addEventListener("click", applyBulkLimitFromForm);
    createDistributionGroupButton.addEventListener("click", handleCreateDistributionGroupClick);
    saveDistributionButton.addEventListener("click", saveDistributionConfig);
    runDeliveryCheckButton.addEventListener("click", runEventDeliveryCheck);
    refreshStatsButton.addEventListener("click", () => loadStatsData(true));

    menuButtons.forEach((button) => {
      button.addEventListener("click", () => setActiveView(button.dataset.view));
    });
"""
