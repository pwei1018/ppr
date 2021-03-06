<template>
<v-container fluid no-gutters class="white pa-0"  v-if="summaryView">
    <v-card flat id="collateral-summary">
      <v-row no-gutters class="summary-header pa-2">
        <v-col cols="auto" class="pa-2">
          <v-icon color="#38598A">mdi-car</v-icon>
          <label class="pl-3"><strong>Collateral</strong></label>
        </v-col>
      </v-row>
      <v-container :class="{'invalid-message': showErrorSummary}">
      <v-row no-gutters v-if="showErrorSummary" class="pa-6">
        <v-col cols="auto">
          <v-icon color="#D3272C">mdi-information-outline</v-icon>
          This step is unfinished
          <router-link id="router-link-collateral" class="invalid-link" :to="{ path: '/add-collateral' }">
            Return to this step to complete it.
          </router-link>
        </v-col>
      </v-row>
      </v-container>
    </v-card>
  </v-container>
  <v-container fluid no-gutters v-else class="pa-0">
    <v-row no-gutters>
      <v-container fluid>
        <v-row no-gutters>
          <v-col cols="auto">Your registration must include one of the following:</v-col>
        </v-row>
        <v-row no-gutters class='pt-6'>
          <v-col cols="auto">
            <b>At least one form of collateral (vehicle or general)</b>
          </v-col>
        </v-row>
        <v-row>
          <v-col>
            <v-btn
                id="btn-add-collateral"
                outlined
                color="primary"
                class="ml-2"
                @click="showAddVehicle=true"
              >
                <v-icon>mdi-domain-plus</v-icon>
                <span>Add Vehicle Collateral</span>
            </v-btn>
          </v-col>
        </v-row>
      </v-container>
    </v-row>
    <div :class="{'invalid-section': invalidSection}">
      <v-expand-transition>
        <v-card flat class="add-collateral-container" v-if="showAddVehicle">
          <edit-collateral
            :activeIndex="activeIndex"
            :invalidSection="invalidSection"
            @resetEvent="resetData"
            />
        </v-card>
      </v-expand-transition>
    </div>
    <v-row no-gutters>
      <v-col>
        <v-data-table
          class="collateral-table"
          :headers="headers"
          :items="vehicleCollateral"
          disable-pagination
          disable-sort
          hide-default-footer
        >
          <template v-slot:item="row" class="vehicle-data-table">
            <tr
              v-if="!showEditVehicle[row.index]"
              :key="row.item.id"
              class="vehicle-row"
            >
              <td
                class="list-item__title"
              >
                {{ row.item.type }}
              </td>
              <td>
                {{ row.item.year }}
              </td>
              <td>{{ row.item.make }}</td>
              <td>{{ row.item.model }}</td>
              <td>{{ row.item.serialNumber }}</td>

              <!-- Action Btns -->
              <td class="actions-cell pt-4">
                <div class="actions">
                  <span class="edit-action">
                    <v-btn text color="primary"
                          :id="'class-' + row.index + '-change-added-btn'"
                          @click="initEdit(row.index)"
                          :disabled="addEditInProgress"
                    >
                      <v-icon small>mdi-pencil</v-icon>
                      <span>Edit</span>
                    </v-btn>
                  </span>

                  <span class="actions__more">
                  <v-menu offset-y left nudge-bottom="4">
                    <template v-slot:activator="{ on }">
                      <v-btn
                        text
                        small
                        v-on="on"
                        color="primary"
                        class="actions__more-actions__btn"
                        :disabled="addEditInProgress">
                        <v-icon>mdi-menu-down</v-icon>
                      </v-btn>
                    </template>
                    <v-list class="actions__more-actions">
                      <v-list-item  @click="removeVehicle(row.index)">
                        <v-list-item-subtitle>
                          <v-icon small>mdi-delete</v-icon>
                          <span class="ml-1">Remove</span>
                        </v-list-item-subtitle>
                      </v-list-item>
                    </v-list>
                  </v-menu>
                </span>
                </div>
              </td>
            </tr>

            <!-- Edit Form -->
            <tr v-if="showEditVehicle[row.index]">
              <td colspan="6" :class="{'invalid-section': invalidSection}">
                <v-expand-transition>
                  <div class="edit-vehicle-container col-9">
                    <edit-collateral
                      :activeIndex="activeIndex"
                      :invalidSection="invalidSection"
                      @removeVehicle="removeVehicle"
                      @resetEvent="resetData"/>
                  </div>
                </v-expand-transition>
              </td>
            </tr>
          </template>
        </v-data-table>
      </v-col>
    </v-row>
    <v-row no-gutters class='pt-6'>
          <v-col cols="auto">
            General Collateral:
          </v-col>
        </v-row>
    <v-row no-gutters>
        <v-col cols="9">
            <v-text-field
              v-model="generalCollateral"
              id="generalCollateral"
              class="white pt-2 text-input-field"
              hint="0 of xxxx characters"
              persistent-hint
            >
          </v-text-field>
        </v-col>
    </v-row>
  </v-container>
</template>

<script lang="ts">
import {
  defineComponent,
  reactive,
  toRefs,
  watch,
  computed
} from '@vue/composition-api'
import { useGetters, useActions } from 'vuex-composition-helpers'
import { AddCollateralIF, VehicleCollateralIF } from '@/interfaces' // eslint-disable-line no-unused-vars
import EditCollateral from './EditCollateral.vue'
import { vehicleTableHeaders } from '@/resources'

export default defineComponent({
  components: {
    EditCollateral //,
    // ActionTypes
  },
  props: {
    isSummary: {
      type: Boolean,
      default: false
    }
  },
  setup (props, { emit }) {
    const { setAddCollateral } = useActions<any>(['setAddCollateral'])
    const { getAddCollateral } = useGetters<any>(['getAddCollateral'])

    const collateral: AddCollateralIF = getAddCollateral.value

    const localState = reactive({
      summaryView: props.isSummary,
      headers: vehicleTableHeaders,
      showAddVehicle: false,
      addEditInProgress: false,
      invalidSection: false,
      activeIndex: -1,
      showEditVehicle: [false],
      vehicleCollateral: collateral.vehicleCollateral,
      generalCollateral: collateral.generalCollateral,
      showErrorSummary: computed((): boolean => {
        return (!collateral.valid)
      })
    })

    watch(() => localState.generalCollateral, (val: string) => {
      collateral.generalCollateral = val
      setAddCollateral(collateral)
      setValid()
    })

    const removeVehicle = (index: number): void => {
      let collateral = getAddCollateral.value // eslint-disable-line
      localState.vehicleCollateral.splice(index, 1)
      collateral.vehicleCollateral = localState.vehicleCollateral
      setAddCollateral(collateral)
      setValid()
    }

    const initEdit = (index: number) => {
      localState.activeIndex = index
      localState.addEditInProgress = true
      localState.showEditVehicle[index] = true
    }

    const resetData = () => {
      localState.activeIndex = -1
      localState.addEditInProgress = false
      localState.showAddVehicle = false
      localState.showEditVehicle = [false]
    }

    const setValid = () => {
      if ((collateral.generalCollateral) || (collateral.vehicleCollateral.length > 0)) {
        collateral.valid = true
      } else {
        collateral.valid = false
      }
      setAddCollateral(collateral)
    }

    return {
      removeVehicle,
      initEdit,
      resetData,
      ...toRefs(localState)
    }
  }
})
</script>

<style lang="scss" module>
@import "@/assets/styles/theme.scss";
.length-trust-label {
  font-size: 0.875rem;
}
</style>
