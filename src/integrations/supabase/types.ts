export type Json =
  | string
  | number
  | boolean
  | null
  | { [key: string]: Json | undefined }
  | Json[]

export type Database = {
  // Allows to automatically instantiate createClient with right options
  // instead of createClient<Database, { PostgrestVersion: 'XX' }>(URL, KEY)
  __InternalSupabase: {
    PostgrestVersion: "14.5"
  }
  public: {
    Tables: {
      agent_runs: {
        Row: {
          context: Json
          final_result: Json | null
          finished_at: string | null
          goal: string
          id: string
          owner_id: string
          started_at: string
          status: string
          tenant_id: string
        }
        Insert: {
          context?: Json
          final_result?: Json | null
          finished_at?: string | null
          goal: string
          id?: string
          owner_id: string
          started_at?: string
          status?: string
          tenant_id: string
        }
        Update: {
          context?: Json
          final_result?: Json | null
          finished_at?: string | null
          goal?: string
          id?: string
          owner_id?: string
          started_at?: string
          status?: string
          tenant_id?: string
        }
        Relationships: []
      }
      agent_steps: {
        Row: {
          action: string | null
          error: string | null
          id: string
          input: Json | null
          observation: Json | null
          run_id: string
          step_index: number
          tenant_id: string
          thought: string | null
          ts: string
        }
        Insert: {
          action?: string | null
          error?: string | null
          id?: string
          input?: Json | null
          observation?: Json | null
          run_id: string
          step_index: number
          tenant_id: string
          thought?: string | null
          ts?: string
        }
        Update: {
          action?: string | null
          error?: string | null
          id?: string
          input?: Json | null
          observation?: Json | null
          run_id?: string
          step_index?: number
          tenant_id?: string
          thought?: string | null
          ts?: string
        }
        Relationships: [
          {
            foreignKeyName: "agent_steps_run_id_fkey"
            columns: ["run_id"]
            isOneToOne: false
            referencedRelation: "agent_runs"
            referencedColumns: ["id"]
          },
        ]
      }
      audit_logs: {
        Row: {
          action: string
          actor_id: string | null
          diff: Json | null
          id: string
          ip: string | null
          resource: string
          resource_id: string | null
          tenant_id: string
          ts: string
          ua: string | null
        }
        Insert: {
          action: string
          actor_id?: string | null
          diff?: Json | null
          id?: string
          ip?: string | null
          resource: string
          resource_id?: string | null
          tenant_id: string
          ts?: string
          ua?: string | null
        }
        Update: {
          action?: string
          actor_id?: string | null
          diff?: Json | null
          id?: string
          ip?: string | null
          resource?: string
          resource_id?: string | null
          tenant_id?: string
          ts?: string
          ua?: string | null
        }
        Relationships: [
          {
            foreignKeyName: "audit_logs_tenant_id_fkey"
            columns: ["tenant_id"]
            isOneToOne: false
            referencedRelation: "tenants"
            referencedColumns: ["id"]
          },
        ]
      }
      capability_studies: {
        Row: {
          computed_at: string
          cp: number | null
          cpk: number | null
          id: string
          metadata: Json
          pp: number | null
          ppk: number | null
          sample_size: number | null
          series_id: string
          tenant_id: string
        }
        Insert: {
          computed_at?: string
          cp?: number | null
          cpk?: number | null
          id?: string
          metadata?: Json
          pp?: number | null
          ppk?: number | null
          sample_size?: number | null
          series_id: string
          tenant_id: string
        }
        Update: {
          computed_at?: string
          cp?: number | null
          cpk?: number | null
          id?: string
          metadata?: Json
          pp?: number | null
          ppk?: number | null
          sample_size?: number | null
          series_id?: string
          tenant_id?: string
        }
        Relationships: [
          {
            foreignKeyName: "capability_studies_series_id_fkey"
            columns: ["series_id"]
            isOneToOne: false
            referencedRelation: "spc_series"
            referencedColumns: ["id"]
          },
        ]
      }
      confusion_matrix_cells: {
        Row: {
          actual_label: string
          count: number
          evaluation_id: string
          id: string
          predicted_label: string
          tenant_id: string
        }
        Insert: {
          actual_label: string
          count?: number
          evaluation_id: string
          id?: string
          predicted_label: string
          tenant_id: string
        }
        Update: {
          actual_label?: string
          count?: number
          evaluation_id?: string
          id?: string
          predicted_label?: string
          tenant_id?: string
        }
        Relationships: [
          {
            foreignKeyName: "confusion_matrix_cells_evaluation_id_fkey"
            columns: ["evaluation_id"]
            isOneToOne: false
            referencedRelation: "model_evaluations"
            referencedColumns: ["id"]
          },
        ]
      }
      dashboards: {
        Row: {
          charts: Json
          created_at: string
          document_id: string
          id: string
          insights: Json
          kpis: Json
          six_sigma: Json | null
          status: string
          tenant_id: string
          updated_at: string
        }
        Insert: {
          charts?: Json
          created_at?: string
          document_id: string
          id?: string
          insights?: Json
          kpis?: Json
          six_sigma?: Json | null
          status?: string
          tenant_id: string
          updated_at?: string
        }
        Update: {
          charts?: Json
          created_at?: string
          document_id?: string
          id?: string
          insights?: Json
          kpis?: Json
          six_sigma?: Json | null
          status?: string
          tenant_id?: string
          updated_at?: string
        }
        Relationships: [
          {
            foreignKeyName: "dashboards_document_id_fkey"
            columns: ["document_id"]
            isOneToOne: true
            referencedRelation: "documents"
            referencedColumns: ["id"]
          },
        ]
      }
      ddr_audit_events: {
        Row: {
          action: string
          actor_id: string
          after: Json | null
          before: Json | null
          ddr_id: string
          id: string
          note: string | null
          tenant_id: string
          ts: string
        }
        Insert: {
          action: string
          actor_id: string
          after?: Json | null
          before?: Json | null
          ddr_id: string
          id?: string
          note?: string | null
          tenant_id: string
          ts?: string
        }
        Update: {
          action?: string
          actor_id?: string
          after?: Json | null
          before?: Json | null
          ddr_id?: string
          id?: string
          note?: string | null
          tenant_id?: string
          ts?: string
        }
        Relationships: [
          {
            foreignKeyName: "ddr_audit_events_ddr_id_fkey"
            columns: ["ddr_id"]
            isOneToOne: false
            referencedRelation: "ddr_reports"
            referencedColumns: ["id"]
          },
        ]
      }
      ddr_metrics: {
        Row: {
          category: string | null
          confidence: number | null
          created_at: string
          ddr_id: string
          id: string
          metadata: Json
          name: string
          source: string | null
          tenant_id: string
          unit: string | null
          updated_at: string
          value_num: number | null
          value_text: string | null
        }
        Insert: {
          category?: string | null
          confidence?: number | null
          created_at?: string
          ddr_id: string
          id?: string
          metadata?: Json
          name: string
          source?: string | null
          tenant_id: string
          unit?: string | null
          updated_at?: string
          value_num?: number | null
          value_text?: string | null
        }
        Update: {
          category?: string | null
          confidence?: number | null
          created_at?: string
          ddr_id?: string
          id?: string
          metadata?: Json
          name?: string
          source?: string | null
          tenant_id?: string
          unit?: string | null
          updated_at?: string
          value_num?: number | null
          value_text?: string | null
        }
        Relationships: [
          {
            foreignKeyName: "ddr_metrics_ddr_id_fkey"
            columns: ["ddr_id"]
            isOneToOne: false
            referencedRelation: "ddr_reports"
            referencedColumns: ["id"]
          },
        ]
      }
      ddr_reports: {
        Row: {
          created_at: string
          document_id: string | null
          id: string
          metadata: Json
          prepared_by: string | null
          report_date: string
          report_no: string | null
          rig_id: string | null
          shift: string | null
          status: string
          summary: string | null
          tenant_id: string
          updated_at: string
          well_id: string | null
        }
        Insert: {
          created_at?: string
          document_id?: string | null
          id?: string
          metadata?: Json
          prepared_by?: string | null
          report_date: string
          report_no?: string | null
          rig_id?: string | null
          shift?: string | null
          status?: string
          summary?: string | null
          tenant_id: string
          updated_at?: string
          well_id?: string | null
        }
        Update: {
          created_at?: string
          document_id?: string | null
          id?: string
          metadata?: Json
          prepared_by?: string | null
          report_date?: string
          report_no?: string | null
          rig_id?: string | null
          shift?: string | null
          status?: string
          summary?: string | null
          tenant_id?: string
          updated_at?: string
          well_id?: string | null
        }
        Relationships: [
          {
            foreignKeyName: "ddr_reports_document_id_fkey"
            columns: ["document_id"]
            isOneToOne: false
            referencedRelation: "documents"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "ddr_reports_rig_id_fkey"
            columns: ["rig_id"]
            isOneToOne: false
            referencedRelation: "rigs"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "ddr_reports_well_id_fkey"
            columns: ["well_id"]
            isOneToOne: false
            referencedRelation: "wells"
            referencedColumns: ["id"]
          },
        ]
      }
      document_chunks: {
        Row: {
          chunk_index: number
          created_at: string
          document_id: string
          embedding: string | null
          id: string
          metadata: Json
          tenant_id: string
          text: string
        }
        Insert: {
          chunk_index: number
          created_at?: string
          document_id: string
          embedding?: string | null
          id?: string
          metadata?: Json
          tenant_id: string
          text: string
        }
        Update: {
          chunk_index?: number
          created_at?: string
          document_id?: string
          embedding?: string | null
          id?: string
          metadata?: Json
          tenant_id?: string
          text?: string
        }
        Relationships: [
          {
            foreignKeyName: "document_chunks_document_id_fkey"
            columns: ["document_id"]
            isOneToOne: false
            referencedRelation: "documents"
            referencedColumns: ["id"]
          },
        ]
      }
      document_edges: {
        Row: {
          created_at: string
          document_id: string | null
          edge_type: string
          id: string
          metadata: Json
          source_id: string
          target_id: string
          tenant_id: string
          weight: number | null
        }
        Insert: {
          created_at?: string
          document_id?: string | null
          edge_type: string
          id?: string
          metadata?: Json
          source_id: string
          target_id: string
          tenant_id: string
          weight?: number | null
        }
        Update: {
          created_at?: string
          document_id?: string | null
          edge_type?: string
          id?: string
          metadata?: Json
          source_id?: string
          target_id?: string
          tenant_id?: string
          weight?: number | null
        }
        Relationships: [
          {
            foreignKeyName: "document_edges_document_id_fkey"
            columns: ["document_id"]
            isOneToOne: false
            referencedRelation: "documents"
            referencedColumns: ["id"]
          },
        ]
      }
      documents: {
        Row: {
          created_at: string
          file_id: string | null
          file_name: string
          has_dashboard: boolean
          id: string
          metadata: Json
          mime: string | null
          owner_id: string
          processing_time_ms: number | null
          provider: string | null
          status: string
          tenant_id: string
          updated_at: string
        }
        Insert: {
          created_at?: string
          file_id?: string | null
          file_name: string
          has_dashboard?: boolean
          id?: string
          metadata?: Json
          mime?: string | null
          owner_id: string
          processing_time_ms?: number | null
          provider?: string | null
          status?: string
          tenant_id: string
          updated_at?: string
        }
        Update: {
          created_at?: string
          file_id?: string | null
          file_name?: string
          has_dashboard?: boolean
          id?: string
          metadata?: Json
          mime?: string | null
          owner_id?: string
          processing_time_ms?: number | null
          provider?: string | null
          status?: string
          tenant_id?: string
          updated_at?: string
        }
        Relationships: [
          {
            foreignKeyName: "documents_file_id_fkey"
            columns: ["file_id"]
            isOneToOne: false
            referencedRelation: "uploaded_files"
            referencedColumns: ["id"]
          },
        ]
      }
      entities: {
        Row: {
          canonical_id: string | null
          created_at: string
          id: string
          metadata: Json
          name: string
          tenant_id: string
          type: string
          updated_at: string
        }
        Insert: {
          canonical_id?: string | null
          created_at?: string
          id?: string
          metadata?: Json
          name: string
          tenant_id: string
          type: string
          updated_at?: string
        }
        Update: {
          canonical_id?: string | null
          created_at?: string
          id?: string
          metadata?: Json
          name?: string
          tenant_id?: string
          type?: string
          updated_at?: string
        }
        Relationships: []
      }
      entity_relations: {
        Row: {
          created_at: string
          id: string
          metadata: Json
          relation: string
          source_entity: string
          target_entity: string
          tenant_id: string
          weight: number | null
        }
        Insert: {
          created_at?: string
          id?: string
          metadata?: Json
          relation: string
          source_entity: string
          target_entity: string
          tenant_id: string
          weight?: number | null
        }
        Update: {
          created_at?: string
          id?: string
          metadata?: Json
          relation?: string
          source_entity?: string
          target_entity?: string
          tenant_id?: string
          weight?: number | null
        }
        Relationships: [
          {
            foreignKeyName: "entity_relations_source_entity_fkey"
            columns: ["source_entity"]
            isOneToOne: false
            referencedRelation: "entities"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "entity_relations_target_entity_fkey"
            columns: ["target_entity"]
            isOneToOne: false
            referencedRelation: "entities"
            referencedColumns: ["id"]
          },
        ]
      }
      fleets: {
        Row: {
          created_at: string
          id: string
          name: string
          region: string | null
          tenant_id: string
          updated_at: string
        }
        Insert: {
          created_at?: string
          id?: string
          name: string
          region?: string | null
          tenant_id: string
          updated_at?: string
        }
        Update: {
          created_at?: string
          id?: string
          name?: string
          region?: string | null
          tenant_id?: string
          updated_at?: string
        }
        Relationships: [
          {
            foreignKeyName: "fleets_tenant_id_fkey"
            columns: ["tenant_id"]
            isOneToOne: false
            referencedRelation: "tenants"
            referencedColumns: ["id"]
          },
        ]
      }
      insights: {
        Row: {
          body: string | null
          created_at: string
          document_id: string | null
          entity_id: string | null
          id: string
          metadata: Json
          severity: string
          tags: string[]
          tenant_id: string
          title: string
          updated_at: string
        }
        Insert: {
          body?: string | null
          created_at?: string
          document_id?: string | null
          entity_id?: string | null
          id?: string
          metadata?: Json
          severity?: string
          tags?: string[]
          tenant_id: string
          title: string
          updated_at?: string
        }
        Update: {
          body?: string | null
          created_at?: string
          document_id?: string | null
          entity_id?: string | null
          id?: string
          metadata?: Json
          severity?: string
          tags?: string[]
          tenant_id?: string
          title?: string
          updated_at?: string
        }
        Relationships: [
          {
            foreignKeyName: "insights_document_id_fkey"
            columns: ["document_id"]
            isOneToOne: false
            referencedRelation: "documents"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "insights_entity_id_fkey"
            columns: ["entity_id"]
            isOneToOne: false
            referencedRelation: "entities"
            referencedColumns: ["id"]
          },
        ]
      }
      job_queue: {
        Row: {
          attempts: number
          created_at: string
          error: string | null
          id: string
          locked_at: string | null
          locked_by: string | null
          max_attempts: number
          payload: Json
          priority: number
          result: Json | null
          run_after: string
          status: string
          tenant_id: string
          type: string
          updated_at: string
        }
        Insert: {
          attempts?: number
          created_at?: string
          error?: string | null
          id?: string
          locked_at?: string | null
          locked_by?: string | null
          max_attempts?: number
          payload?: Json
          priority?: number
          result?: Json | null
          run_after?: string
          status?: string
          tenant_id: string
          type: string
          updated_at?: string
        }
        Update: {
          attempts?: number
          created_at?: string
          error?: string | null
          id?: string
          locked_at?: string | null
          locked_by?: string | null
          max_attempts?: number
          payload?: Json
          priority?: number
          result?: Json | null
          run_after?: string
          status?: string
          tenant_id?: string
          type?: string
          updated_at?: string
        }
        Relationships: [
          {
            foreignKeyName: "job_queue_tenant_id_fkey"
            columns: ["tenant_id"]
            isOneToOne: false
            referencedRelation: "tenants"
            referencedColumns: ["id"]
          },
        ]
      }
      model_evaluations: {
        Row: {
          accuracy: number | null
          computed_at: string
          f1: number | null
          id: string
          metrics: Json
          model_name: string
          precision: number | null
          recall: number | null
          task: string | null
          tenant_id: string
          version: string | null
        }
        Insert: {
          accuracy?: number | null
          computed_at?: string
          f1?: number | null
          id?: string
          metrics?: Json
          model_name: string
          precision?: number | null
          recall?: number | null
          task?: string | null
          tenant_id: string
          version?: string | null
        }
        Update: {
          accuracy?: number | null
          computed_at?: string
          f1?: number | null
          id?: string
          metrics?: Json
          model_name?: string
          precision?: number | null
          recall?: number | null
          task?: string | null
          tenant_id?: string
          version?: string | null
        }
        Relationships: []
      }
      profiles: {
        Row: {
          avatar_url: string | null
          created_at: string
          display_name: string | null
          email: string
          id: string
          tenant_id: string
          updated_at: string
        }
        Insert: {
          avatar_url?: string | null
          created_at?: string
          display_name?: string | null
          email: string
          id: string
          tenant_id: string
          updated_at?: string
        }
        Update: {
          avatar_url?: string | null
          created_at?: string
          display_name?: string | null
          email?: string
          id?: string
          tenant_id?: string
          updated_at?: string
        }
        Relationships: [
          {
            foreignKeyName: "profiles_tenant_id_fkey"
            columns: ["tenant_id"]
            isOneToOne: false
            referencedRelation: "tenants"
            referencedColumns: ["id"]
          },
        ]
      }
      rigs: {
        Row: {
          contractor: string | null
          created_at: string
          fleet_id: string | null
          id: string
          metadata: Json
          rig_no: string
          status: string
          tenant_id: string
          updated_at: string
        }
        Insert: {
          contractor?: string | null
          created_at?: string
          fleet_id?: string | null
          id?: string
          metadata?: Json
          rig_no: string
          status?: string
          tenant_id: string
          updated_at?: string
        }
        Update: {
          contractor?: string | null
          created_at?: string
          fleet_id?: string | null
          id?: string
          metadata?: Json
          rig_no?: string
          status?: string
          tenant_id?: string
          updated_at?: string
        }
        Relationships: [
          {
            foreignKeyName: "rigs_fleet_id_fkey"
            columns: ["fleet_id"]
            isOneToOne: false
            referencedRelation: "fleets"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "rigs_tenant_id_fkey"
            columns: ["tenant_id"]
            isOneToOne: false
            referencedRelation: "tenants"
            referencedColumns: ["id"]
          },
        ]
      }
      spc_points: {
        Row: {
          id: string
          metadata: Json
          out_of_control: boolean
          rule_flags: string[]
          series_id: string
          tenant_id: string
          ts: string
          value: number
        }
        Insert: {
          id?: string
          metadata?: Json
          out_of_control?: boolean
          rule_flags?: string[]
          series_id: string
          tenant_id: string
          ts: string
          value: number
        }
        Update: {
          id?: string
          metadata?: Json
          out_of_control?: boolean
          rule_flags?: string[]
          series_id?: string
          tenant_id?: string
          ts?: string
          value?: number
        }
        Relationships: [
          {
            foreignKeyName: "spc_points_series_id_fkey"
            columns: ["series_id"]
            isOneToOne: false
            referencedRelation: "spc_series"
            referencedColumns: ["id"]
          },
        ]
      }
      spc_series: {
        Row: {
          chart_type: string
          created_at: string
          id: string
          lcl: number | null
          metadata: Json
          metric_name: string
          rig_id: string | null
          target: number | null
          tenant_id: string
          ucl: number | null
          unit: string | null
          updated_at: string
          well_id: string | null
        }
        Insert: {
          chart_type?: string
          created_at?: string
          id?: string
          lcl?: number | null
          metadata?: Json
          metric_name: string
          rig_id?: string | null
          target?: number | null
          tenant_id: string
          ucl?: number | null
          unit?: string | null
          updated_at?: string
          well_id?: string | null
        }
        Update: {
          chart_type?: string
          created_at?: string
          id?: string
          lcl?: number | null
          metadata?: Json
          metric_name?: string
          rig_id?: string | null
          target?: number | null
          tenant_id?: string
          ucl?: number | null
          unit?: string | null
          updated_at?: string
          well_id?: string | null
        }
        Relationships: [
          {
            foreignKeyName: "spc_series_rig_id_fkey"
            columns: ["rig_id"]
            isOneToOne: false
            referencedRelation: "rigs"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "spc_series_well_id_fkey"
            columns: ["well_id"]
            isOneToOne: false
            referencedRelation: "wells"
            referencedColumns: ["id"]
          },
        ]
      }
      tenants: {
        Row: {
          created_at: string
          id: string
          name: string
          plan: string
          settings: Json
          slug: string
          updated_at: string
        }
        Insert: {
          created_at?: string
          id?: string
          name: string
          plan?: string
          settings?: Json
          slug: string
          updated_at?: string
        }
        Update: {
          created_at?: string
          id?: string
          name?: string
          plan?: string
          settings?: Json
          slug?: string
          updated_at?: string
        }
        Relationships: []
      }
      uploaded_files: {
        Row: {
          bucket: string
          created_at: string
          id: string
          metadata: Json
          mime: string | null
          owner_id: string
          path: string
          sha256: string | null
          size: number | null
          status: string
          tenant_id: string
          updated_at: string
        }
        Insert: {
          bucket?: string
          created_at?: string
          id?: string
          metadata?: Json
          mime?: string | null
          owner_id: string
          path: string
          sha256?: string | null
          size?: number | null
          status?: string
          tenant_id: string
          updated_at?: string
        }
        Update: {
          bucket?: string
          created_at?: string
          id?: string
          metadata?: Json
          mime?: string | null
          owner_id?: string
          path?: string
          sha256?: string | null
          size?: number | null
          status?: string
          tenant_id?: string
          updated_at?: string
        }
        Relationships: [
          {
            foreignKeyName: "uploaded_files_tenant_id_fkey"
            columns: ["tenant_id"]
            isOneToOne: false
            referencedRelation: "tenants"
            referencedColumns: ["id"]
          },
        ]
      }
      user_roles: {
        Row: {
          created_at: string
          id: string
          role: Database["public"]["Enums"]["app_role"]
          tenant_id: string
          user_id: string
        }
        Insert: {
          created_at?: string
          id?: string
          role: Database["public"]["Enums"]["app_role"]
          tenant_id: string
          user_id: string
        }
        Update: {
          created_at?: string
          id?: string
          role?: Database["public"]["Enums"]["app_role"]
          tenant_id?: string
          user_id?: string
        }
        Relationships: [
          {
            foreignKeyName: "user_roles_tenant_id_fkey"
            columns: ["tenant_id"]
            isOneToOne: false
            referencedRelation: "tenants"
            referencedColumns: ["id"]
          },
        ]
      }
      wells: {
        Row: {
          created_at: string
          field: string | null
          id: string
          rig_id: string | null
          spud_date: string | null
          status: string
          td_date: string | null
          tenant_id: string
          updated_at: string
          well_name: string
        }
        Insert: {
          created_at?: string
          field?: string | null
          id?: string
          rig_id?: string | null
          spud_date?: string | null
          status?: string
          td_date?: string | null
          tenant_id: string
          updated_at?: string
          well_name: string
        }
        Update: {
          created_at?: string
          field?: string | null
          id?: string
          rig_id?: string | null
          spud_date?: string | null
          status?: string
          td_date?: string | null
          tenant_id?: string
          updated_at?: string
          well_name?: string
        }
        Relationships: [
          {
            foreignKeyName: "wells_rig_id_fkey"
            columns: ["rig_id"]
            isOneToOne: false
            referencedRelation: "rigs"
            referencedColumns: ["id"]
          },
          {
            foreignKeyName: "wells_tenant_id_fkey"
            columns: ["tenant_id"]
            isOneToOne: false
            referencedRelation: "tenants"
            referencedColumns: ["id"]
          },
        ]
      }
    }
    Views: {
      [_ in never]: never
    }
    Functions: {
      current_tenant_id: { Args: never; Returns: string }
      has_role: {
        Args: {
          _role: Database["public"]["Enums"]["app_role"]
          _user_id: string
        }
        Returns: boolean
      }
      has_tenant_role: {
        Args: { _role: Database["public"]["Enums"]["app_role"] }
        Returns: boolean
      }
    }
    Enums: {
      app_role:
        | "super_admin"
        | "tenant_admin"
        | "ops_manager"
        | "drilling_engineer"
        | "analyst"
        | "viewer"
        | "api_service"
    }
    CompositeTypes: {
      [_ in never]: never
    }
  }
}

type DatabaseWithoutInternals = Omit<Database, "__InternalSupabase">

type DefaultSchema = DatabaseWithoutInternals[Extract<keyof Database, "public">]

export type Tables<
  DefaultSchemaTableNameOrOptions extends
    | keyof (DefaultSchema["Tables"] & DefaultSchema["Views"])
    | { schema: keyof DatabaseWithoutInternals },
  TableName extends DefaultSchemaTableNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof (DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"] &
        DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Views"])
    : never = never,
> = DefaultSchemaTableNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? (DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"] &
      DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Views"])[TableName] extends {
      Row: infer R
    }
    ? R
    : never
  : DefaultSchemaTableNameOrOptions extends keyof (DefaultSchema["Tables"] &
        DefaultSchema["Views"])
    ? (DefaultSchema["Tables"] &
        DefaultSchema["Views"])[DefaultSchemaTableNameOrOptions] extends {
        Row: infer R
      }
      ? R
      : never
    : never

export type TablesInsert<
  DefaultSchemaTableNameOrOptions extends
    | keyof DefaultSchema["Tables"]
    | { schema: keyof DatabaseWithoutInternals },
  TableName extends DefaultSchemaTableNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"]
    : never = never,
> = DefaultSchemaTableNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"][TableName] extends {
      Insert: infer I
    }
    ? I
    : never
  : DefaultSchemaTableNameOrOptions extends keyof DefaultSchema["Tables"]
    ? DefaultSchema["Tables"][DefaultSchemaTableNameOrOptions] extends {
        Insert: infer I
      }
      ? I
      : never
    : never

export type TablesUpdate<
  DefaultSchemaTableNameOrOptions extends
    | keyof DefaultSchema["Tables"]
    | { schema: keyof DatabaseWithoutInternals },
  TableName extends DefaultSchemaTableNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"]
    : never = never,
> = DefaultSchemaTableNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? DatabaseWithoutInternals[DefaultSchemaTableNameOrOptions["schema"]]["Tables"][TableName] extends {
      Update: infer U
    }
    ? U
    : never
  : DefaultSchemaTableNameOrOptions extends keyof DefaultSchema["Tables"]
    ? DefaultSchema["Tables"][DefaultSchemaTableNameOrOptions] extends {
        Update: infer U
      }
      ? U
      : never
    : never

export type Enums<
  DefaultSchemaEnumNameOrOptions extends
    | keyof DefaultSchema["Enums"]
    | { schema: keyof DatabaseWithoutInternals },
  EnumName extends DefaultSchemaEnumNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof DatabaseWithoutInternals[DefaultSchemaEnumNameOrOptions["schema"]]["Enums"]
    : never = never,
> = DefaultSchemaEnumNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? DatabaseWithoutInternals[DefaultSchemaEnumNameOrOptions["schema"]]["Enums"][EnumName]
  : DefaultSchemaEnumNameOrOptions extends keyof DefaultSchema["Enums"]
    ? DefaultSchema["Enums"][DefaultSchemaEnumNameOrOptions]
    : never

export type CompositeTypes<
  PublicCompositeTypeNameOrOptions extends
    | keyof DefaultSchema["CompositeTypes"]
    | { schema: keyof DatabaseWithoutInternals },
  CompositeTypeName extends PublicCompositeTypeNameOrOptions extends {
    schema: keyof DatabaseWithoutInternals
  }
    ? keyof DatabaseWithoutInternals[PublicCompositeTypeNameOrOptions["schema"]]["CompositeTypes"]
    : never = never,
> = PublicCompositeTypeNameOrOptions extends {
  schema: keyof DatabaseWithoutInternals
}
  ? DatabaseWithoutInternals[PublicCompositeTypeNameOrOptions["schema"]]["CompositeTypes"][CompositeTypeName]
  : PublicCompositeTypeNameOrOptions extends keyof DefaultSchema["CompositeTypes"]
    ? DefaultSchema["CompositeTypes"][PublicCompositeTypeNameOrOptions]
    : never

export const Constants = {
  public: {
    Enums: {
      app_role: [
        "super_admin",
        "tenant_admin",
        "ops_manager",
        "drilling_engineer",
        "analyst",
        "viewer",
        "api_service",
      ],
    },
  },
} as const
