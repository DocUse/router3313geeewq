GROUPS_PAGE_SCRIPT_DATA = """    async function fetchJson(url, options) {
      const response = await fetch(url, options);
      const responseText = await response.text();
      let payload = {};
      if (responseText) {
        try {
          payload = JSON.parse(responseText);
        } catch (error) {
          payload = {};
        }
      }
      if (!response.ok) {
        throw new Error(payload.detail || responseText || `Backend returned HTTP ${response.status}.`);
      }
      return payload;
    }

    function getBitrixAuth() {
      return new Promise((resolve) => {
        if (!window.BX24 || typeof window.BX24.init !== "function" || typeof window.BX24.getAuth !== "function") {
          resolve(null);
          return;
        }

        try {
          window.BX24.init(() => {
            const auth = window.BX24.getAuth();
            resolve(auth || null);
          });
        } catch (error) {
          console.error("BX24 auth initialization failed", error);
          resolve(null);
        }
      });
    }

    async function resolveBitrixAuth() {
      if (distributionState.auth) {
        return distributionState.auth;
      }

      const auth = await getBitrixAuth();
      distributionState.auth = auth;
      if (!distributionState.memberId && auth && auth.member_id) {
        distributionState.memberId = auth.member_id;
      }
      return distributionState.auth;
    }

    async function resolveDistributionMemberId() {
      if (distributionState.memberId) {
        return distributionState.memberId;
      }

      const auth = await resolveBitrixAuth();
      const bitrixMemberId = (auth && auth.member_id) || "";
      distributionState.memberId = bitrixMemberId;
      return distributionState.memberId;
    }

    async function syncPortalContextFromBitrix() {
      const auth = await resolveBitrixAuth();
      if (!auth || !auth.member_id || !auth.domain || !auth.access_token) {
        return;
      }

      const payload = {
        member_id: auth.member_id,
        DOMAIN: auth.domain,
        AUTH_ID: auth.access_token,
        REFRESH_ID: auth.refresh_token || "",
        PROTOCOL: "1",
      };

      const response = await fetch("/api/ui/groups/portal-context", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(payload),
      });

      if (!response.ok) {
        const errorPayload = await response.json().catch(() => ({}));
        throw new Error(errorPayload.detail || "Не удалось синхронизировать портал с backend.");
      }
    }

    async function loadStatsData(forceReload) {
      if (statsState.isLoading) {
        return;
      }
      if (statsState.isLoaded && !forceReload) {
        renderStatsData(statsState.data || {});
        return;
      }

      const distributionMemberId = await resolveDistributionMemberId();
      if (!distributionMemberId) {
        setStatsStatus("Не удалось определить member_id портала для загрузки статистики.", "is-error");
        renderStatsEmpty(statsSummaryList, "Нет portal context.");
        renderStatsEmpty(statsMembersList, "Нет portal context.");
        renderStatsEmpty(statsDiagnosticsList, "Нет portal context.");
        renderStatsEmpty(statsJournalList, "Нет portal context.");
        return;
      }

      statsState.isLoading = true;
      setStatsStatus("Загружаем журнал распределения...");
      try {
        await syncPortalContextFromBitrix();
        const payload = await fetchJson(`/api/ui/stats?member_id=${encodeURIComponent(distributionMemberId)}`);
        statsState.data = payload;
        statsState.isLoaded = true;
        renderStatsData(payload);
        setStatsStatus("Журнал и runtime-данные обновлены.", "is-success");
      } catch (error) {
        setStatsStatus(error.message || "Не удалось загрузить статистику.", "is-error");
        renderStatsEmpty(statsSummaryList, "Статистика пока недоступна.");
        renderStatsEmpty(statsMembersList, "Статистика пока недоступна.");
        renderStatsEmpty(statsDiagnosticsList, "Статистика пока недоступна.");
        renderStatsEmpty(statsJournalList, "Статистика пока недоступна.");
      } finally {
        statsState.isLoading = false;
      }
    }

    async function loadDistributionReferenceData() {
      if (distributionState.isLoaded || distributionState.isLoading) {
        if (distributionState.isLoaded) {
          if (distributionState.openFormRequested) {
            renderDistributionConfigForm();
          }
        }
        return;
      }

      const distributionMemberId = await resolveDistributionMemberId();
      if (!distributionMemberId) {
        if (distributionState.openFormRequested) {
          showDistributionLanding();
          setDistributionStatus(
            "Не удалось определить member_id портала. Откройте приложение внутри Bitrix24 или завершите повторную установку, чтобы загрузить реальные справочники.",
            "is-error"
          );
        }
        return;
      }

      distributionState.isLoading = true;
      if (distributionState.openFormRequested) {
        showDistributionForm();
        distributionForm.hidden = true;
        setDistributionStatus("Загружаем данные портала и конфигурацию группы...");
      }

      try {
        await syncPortalContextFromBitrix();
        const [referencePayload, configPayload] = await Promise.all([
          fetchJson(`/api/ui/groups/reference-data?member_id=${encodeURIComponent(distributionMemberId)}`),
          fetchJson(`/api/ui/groups/config?member_id=${encodeURIComponent(distributionMemberId)}`),
        ]);

        distributionState.referenceData = referencePayload;
        distributionState.config = normalizeLoadedDistributionConfig(configPayload.config, referencePayload);
        distributionState.isLoaded = true;
        if (distributionState.openFormRequested) {
          renderDistributionConfigForm();
          if (configPayload.config) {
            setDistributionStatus("Сохраненная конфигурация группы загружена. Изменения применяются кнопкой «Применить».", "is-success");
          } else {
            setDistributionStatus("Справочники Bitrix24 загружены. Заполните форму и нажмите «Применить».", "is-success");
          }
        } else {
          showDistributionLanding();
        }
      } catch (error) {
        if (distributionState.openFormRequested) {
          showDistributionLanding();
          setDistributionStatus(error.message || "Не удалось загрузить форму распределения.", "is-error");
        }
      } finally {
        distributionState.isLoading = false;
      }
    }
"""
